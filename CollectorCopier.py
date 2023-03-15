import shutil
import os
import threading
import re
import time
import json
from json import JSONEncoder
import subprocess
from queue import Queue
import sys

sys.path.append(r"R:\pipeline\networkInstall\arnold\Arnold-7.1.4.1-windows")
from arnold import *

from utils import *

try:
    from pymel.all import *
except:
    # Maya not found
    pass

# ######################################################################################################################

_RANCH_SERVER = "RANCH-126"
_RANCH_FOLDER = "ranch_cache"
_MAX_NB_THREADs = 256

_LOGS_FOLDER = "I:/logs"
_ASS_PATHS_FILE_EXTENSION = "paths"
_FORCE_CREATION_ASS_PATHS_FILES = False

# ######################################################################################################################

# 18 + Length of longer message possible (here : "File already exists")
_LENGTH_PADDING = 18 + 19
_LENGTH_HEADER_FOOTER = 200


class CollectorCopier:

    # Generate the dict data for a path
    @staticmethod
    def __generate_data_for_path(path):
        match = re.match(r"^([A-Z]):[\\/](.*)$", path)
        if match:
            disk_letter = match.group(1)
            path_without_disk_letter = match.group(2)
            destination = os.path.join("\\\\", _RANCH_SERVER, _RANCH_FOLDER, disk_letter, path_without_disk_letter)
            return {
                "src": path.replace("\\", "/"),
                "dest": destination,
                "folder_dest": os.path.dirname(destination),
                "size": os.path.getsize(path)
            }
        return None

    def __init__(self):
        self.__datas = []
        self.__scene_path = ""
        self.__log_file_name = ""
        self.__log_file = None
        self.__data_file_name = ""
        self.__scene_datas = {}
        self.__reinit_copy_attributes()
        self.__datas_lock = threading.Lock()
        self.__progress_lock = threading.Lock()
        self.__output_queue = Queue()
        self.__output_enabled = True

    def retrieve_datas(self, file_data_path):
        self.__data_file_name = file_data_path
        f = open(self.__data_file_name, "r")
        json_dict = f.read()
        f.close()
        os.remove(self.__data_file_name)
        collector_copier_dict = json.loads(json_dict)
        self.__datas = collector_copier_dict["datas"] if "datas" in collector_copier_dict else []
        self.__scene_path = collector_copier_dict["scene_path"] if "scene_path" in collector_copier_dict else ""
        self.__log_file_name = collector_copier_dict[
            "file_logs_name"] if "file_logs_name" in collector_copier_dict else ""
        self.__reinit_copy_attributes()

    def __store_datas(self):
        collector_copier_dict = {
            "datas": self.__datas,
            "scene_path": self.__scene_path,
            "file_logs_name": self.__log_file_name
        }
        json_dict = json.dumps(collector_copier_dict)
        f = open(self.__data_file_name, "w")
        f.write(json_dict)
        f.close()

    # Init some attributes for the copy and logs
    def __reinit_copy_attributes(self):
        self.__total_file_size = 0
        self.__current_file_size = 0
        self.__total_file_nb = 0
        self.__current_file_nb = 0
        self.__current_data_index = 0
        self.__datas_length = len(self.__datas)
        self.__max_length_path = 0

    def __output(self, msg, print_msg=True):
        self.__log_file.write(msg + "\n")
        self.__log_file.flush()
        if print_msg:
            print(msg, flush=True)

    # Output the logs in a file and text
    def __thread_output(self):
        while self.__output_enabled or not self.__output_queue.empty():
            if not self.__output_queue.empty():
                msg = self.__output_queue.get_nowait()
                self.__output(msg, False)
            else:
                # Allow most important threads to work before checking if a message is available
                time.sleep(0.01)

    # Copy with datas to Ranch
    def __copy_from_data(self, data):
        count_file_str_length = 2 * len(str(self.__datas_length)) + 1
        str_length = self.__max_length_path + count_file_str_length + _LENGTH_PADDING
        os.makedirs(data['folder_dest'], exist_ok=True)
        path_src = data["src"]
        path_dest = data["dest"]
        size_src = data["size"]

        # Check whether the file need to by copied
        do_copy = True
        if os.path.exists(path_dest):
            mtime_src = os.path.getmtime(path_src)
            mtime_dest = os.path.getmtime(path_dest)
            size_dest = os.path.getsize(path_dest)
            if mtime_src == mtime_dest and size_dest == size_src:
                do_copy = False

        if do_copy:
            # Copy
            shutil.copy2(path_src, path_dest)

        # Output Logs
        with self.__progress_lock:
            self.__current_file_size += size_src
            self.__current_file_nb += 1
            percent_copied = round(self.__current_file_size / self.__total_file_size * 100, 2)
            str_percent = str(percent_copied).rjust(5) + "%"
            str_file_count = (str(self.__current_file_nb) + "/" + str(self.__total_file_nb)).rjust(
                count_file_str_length)
            msg = "Copy On RANCH of" if do_copy else "File already exists"
            complete_msg = "| " + str_percent + " - " + str_file_count + " - " + msg + " : " + path_src + " "
            self.__output_queue.put(complete_msg.ljust(str_length, " ") + "|")

    # Thread of copy : It takes the data of the current file and copy it. It then take the next available
    def __thread_copy_file(self):
        file_available = True
        while file_available:
            # Increment current data Index
            with self.__datas_lock:
                index_data = self.__current_data_index
                self.__current_data_index += 1
            # Stop iterating through data if end reached
            if self.__current_data_index > self.__datas_length:
                file_available = False
            else:
                file_datas = self.__datas[index_data]
                # Copy the current file
                self.__copy_from_data(file_datas)

    def __thread_scene(self):
        self.__copy_from_data(self.__scene_datas)

    # Copy all the files retrieved
    def __copy(self):
        # Sort the files according to their size to be more efficient.
        # Ex :
        # Thread1 ---------------- | ------------ | --------
        # Thread2 --------------- | ----------- | ------- | ---
        # Thread3 ------------- | --------- | ------ | ---- | -
        #                Better than :
        # Thread1 - | ------ | --------- | -------------
        # Thread2 --- | ------- | ----------- | ---------------
        # Thread3 ---- | -------- | ------------ | ----------------
        self.__datas.sort(key=lambda x: x.get("size"), reverse=True)

        # Init datas and copy attributes
        self.__reinit_copy_attributes()
        self.__total_file_nb = len(self.__datas)
        for data_copy in self.__datas:
            self.__total_file_size += data_copy["size"]
            self.__max_length_path = max(self.__max_length_path, len(data_copy["src"]))
        self.__total_file_size += self.__scene_datas["size"]
        self.__total_file_nb += 1
        self.__max_length_path = max(self.__max_length_path, len(self.__scene_datas["src"]))
        threads = []

        count_file_str_length = 2 * len(str(self.__datas_length)) + 1

        # Compute the good number of threads
        nb_thread = min(self.__total_file_nb, _MAX_NB_THREADs)

        # Start All Threads
        with self.__progress_lock:
            msg = "+- Copy On RANCH : " + str(nb_thread) + " threads launched for " + str(
                self.__total_file_nb) + " file(s) "

            self.__output_queue.put(
                "\n" + msg.ljust(self.__max_length_path + count_file_str_length + _LENGTH_PADDING, "-") + "+")
        for i in range(nb_thread):
            th = threading.Thread(target=self.__thread_copy_file)
            threads.append(th)
            th.start()
        # Join All Threads
        for th in threads:
            th.join()
        # At the end when all files have been copied we can copy the scene
        with self.__datas_lock:
            th = threading.Thread(target=self.__thread_scene)
            th.start()
            th.join()
            # self.__copy_from_data(self.__scene_datas)

        with self.__progress_lock:
            msg = "+- Copy On RANCH Finished "

            self.__output_queue.put(
                msg.ljust(self.__max_length_path + count_file_str_length + _LENGTH_PADDING, "-") + "+")

    # Retrieve all the paths used in Maya Scene
    def __retrieve_paths_in_maya(self):
        count_path = 1
        list_files = ls(type="file")
        list_standins = ls(type='aiStandIn')
        list_refs = ls(references=True)
        nb_tot = len(list_files) + len(list_standins) + len(list_refs)
        paths = []
        # FILES
        self.__output("| ----- Retrieve paths in FileNodes")
        for file in list_files:
            path = file.fileTextureName.get()
            if os.path.exists(path):
                self.__output(
                    "| " + str(count_path) + "/" + str(nb_tot) + " - FileNode path found : " + path)
                paths.append(path)
            else:
                self.__output(
                    "| " + str(count_path) + "/" + str(nb_tot) + " - Error FileNode path do not exists : " + path)
            count_path += 1
        # STANDIN
        self.__output("| ----- Retrieve paths in StandIns")
        for standin in list_standins:
            path = standin.dso.get()
            standin_error = False
            if standin.useFrameExtension.get():
                dir_path = os.path.dirname(path)
                if os.path.exists(dir_path):
                    self.__output(
                        "| " + str(count_path) + "/" + str(nb_tot) + " - StandIn sequence found in : " + dir_path + "/")
                    for f in os.listdir(dir_path):
                        if len(f)<6 or f[-6:] != "."+ _ASS_PATHS_FILE_EXTENSION:
                            child_path = os.path.join(dir_path, f)
                            self.__output("|    +----> " + child_path)
                            paths.append(child_path)
                else:
                    standin_error = True
            elif os.path.exists(path):
                self.__output(
                    "| " + str(count_path) + "/" + str(nb_tot) + " - StandIn dso found : " + path)
                paths.append(path)
            else:
                standin_error = True
            if standin_error:
                self.__output(
                    "| " + str(count_path) + "/" + str(nb_tot) + " - Error StandIn dso do not exists : " + path)
            count_path += 1
        # REFERENCES
        self.__output("| ----- Retrieve paths in References")
        for ref in list_refs:
            path = referenceQuery(ref, filename=True)
            if os.path.exists(path):
                self.__output("| " + str(count_path) + "/" + str(nb_tot) + " - Reference path found : " + path)
                paths.append(path)
            else:
                self.__output(
                    "| " + str(count_path) + "/" + str(nb_tot) + " - Error Reference path do not exists : " + path)
            count_path += 1
        nb_added = 0
        for path in paths:
            if path not in self.__datas:
                nb_added+=1
                self.__datas.append(path)
        return nb_added

    def __retrieve_ass_paths(self):
        list_standin = ls(type='aiStandIn')
        ass_paths_count = 0
        i = 1
        dsos = []
        for standin in list_standin:
            dso = standin.dso.get()
            if dso not in dsos:
                dsos.append(dso)

        nb_dsos = len(dsos)
        # Iterate through StandIn
        for dso in dsos:
            AiBegin(AI_SESSION_BATCH)
            AiMsgSetConsoleFlags(AI_LOG_ALL)
            ass_paths = []
            relative_paths = []
            texture_search_paths = []
            match = re.match(r"^(.*)\.\w*$", os.path.basename(dso))
            paths_info_filepath = os.path.join(os.path.dirname(dso), match.group(1) + "." + _ASS_PATHS_FILE_EXTENSION)

            paths_info_file_exits = os.path.exists(paths_info_filepath)

            str_dso_count = str(i) + "/" + str(nb_dsos)
            if paths_info_file_exits and not _FORCE_CREATION_ASS_PATHS_FILES:
                self.__output(
                    "| " + str_dso_count + " - Paths info already exists for " + dso)
                path_info_file = open(paths_info_filepath, "r")
                ass_paths = json.loads(path_info_file.read())
                if len(ass_paths) > 0:
                    self.__output("\n".join(["|    +----> " + path for path in ass_paths]))
            else:
                if paths_info_file_exits:
                    open(paths_info_filepath, "w").close()

                path_info_file = open(paths_info_filepath, "a")

                AiASSLoad(dso)
                self.__output("| " + str_dso_count + " - Search in " + dso)
                # Iterate through Node in StandIn that are Options or Shaders
                iterator = AiUniverseGetNodeIterator(AI_NODE_SHADER | AI_NODE_OPTIONS)
                while not AiNodeIteratorFinished(iterator):
                    node = AiNodeIteratorGetNext(iterator)
                    node_name = AiNodeGetName(node)
                    if node_name:
                        is_image = AiNodeIs(node, "image")
                        is_options = AiNodeIs(node, "options")
                        # If IMAGE Retrieve the filepath
                        if is_image:
                            filename = AiNodeGetStr(node, "filename")
                            if len(filename) > 0 and filename not in relative_paths:
                                relative_paths.append(filename)
                        # IF OPTIONS Retrieve the texture search path
                        elif is_options and len(texture_search_paths) == 0:
                            texture_search_paths = AiNodeGetStr(node, "texture_searchpath")

                AiNodeIteratorDestroy(iterator)
                if len(relative_paths) > 0:
                    for base_path in texture_search_paths.split(";"):
                        # If all file processed stop the search
                        if len(relative_paths) == 0:
                            break

                        # Try to find if the path is a reference to an env var
                        match = re.match(r"^\[(\w+)]$", base_path)
                        if match:
                            env_var_name = match.group(1)
                            env_var = os.getenv(env_var_name)
                            if env_var:
                                base_path = env_var

                        # For each file try to base_path, If exists remove the file from the list to processed
                        rel_path_to_remove = []
                        for rel_path in relative_paths:
                            absolute_path = os.path.join(base_path, rel_path)
                            if os.path.exists(absolute_path):
                                ass_paths.append(absolute_path)
                                self.__output("|    +----> " + absolute_path)
                                rel_path_to_remove.append(rel_path)
                        if len(rel_path_to_remove) > 0:
                            for rel_path in rel_path_to_remove:
                                relative_paths.remove(rel_path)

                path_info_file.write(json.dumps(ass_paths))
                path_info_file.close()

            path_info_file = open(paths_info_filepath, "r")
            ass_paths = json.loads(path_info_file.read())
            ass_paths_count += len(ass_paths)
            self.__datas.extend(ass_paths)
            AiEnd()
            i += 1
        return ass_paths_count

    # Generate all the datas from the file path
    def __generate_ranged_cache_dest(self):
        ranged_cache_paths = []
        for path in self.__datas:
            data = CollectorCopier.__generate_data_for_path(path)
            if data is not None:
                ranged_cache_paths.append(data)
        self.__datas = ranged_cache_paths
        if os.path.exists(self.__scene_path):
            scene_datas = CollectorCopier.__generate_data_for_path(self.__scene_path)
            if scene_datas is not None:
                self.__scene_datas = scene_datas

    def __generate_log_data(self):
        scene_dirname, scene_basename = os.path.split(self.__scene_path)
        match_name = re.match(r"^(.*)\.(?:ma|mb)$", scene_basename)
        scene_name = match_name.group(1)
        match_dir = re.match(r"^[A-Z]:[\\/](\w*)[\\/].*$", scene_dirname)
        project = match_dir.group(1)
        folder = os.path.join(_LOGS_FOLDER, project)
        os.makedirs(folder, exist_ok=True)
        name_file = os.path.join(folder, time.strftime("%Y_%m_%d_%H%M%S") + "_" + scene_name)
        self.__log_file_name = name_file + ".log"
        self.__data_file_name = name_file + ".data"

    # Generate the logs file name and the Header
    def __header_log(self):
        padding_length = (_LENGTH_HEADER_FOOTER - 21) // 2
        header = padding_length * "#" + " " + time.strftime("%Y-%m-%d %H:%M:%S") + " " + padding_length * "#"
        self.__output(header, False)

    # Generate the Footer
    def __footer_log(self):
        footer = _LENGTH_HEADER_FOOTER * "#"
        self.__output_queue.put(footer, False)

    def __start_log(self):
        self.__log_file = open(self.__log_file_name, "a")

    def __start_thread_log(self):
        self.__output_enabled = True
        self.__thread_output = threading.Thread(target=self.__thread_output)
        self.__thread_output.start()

    def __stop_log(self):
        self.__output_enabled = False
        self.__thread_output.join()
        self.__log_file.close()

    # Run Collector and Copier to Ranch
    def run_collect(self):
        self.__datas.clear()
        self.__scene_path = sceneName()

        if len(self.__scene_path) == 0:
            print("----- SCENE NOT FOUND -----")
            return

        self.__generate_log_data()

        self.__start_log()

        self.__header_log()

        # # MAYA PATHS
        self.__output("\n+- Start retrieve all the paths in Maya -----")
        nb_maya_paths = self.__retrieve_paths_in_maya()
        self.__output("+- End retrieve all the paths in Maya [" + str(nb_maya_paths) + "] -----")

        self.__start_thread_log()

        # ASS PATHS
        self.__output("\n+- Start retrieve all the paths in ASS files -----")
        nb_ass_paths = self.__retrieve_ass_paths()
        self.__output("+- End retrieve all the paths in ASS files [" + str(nb_ass_paths) + "] -----")

        # COPY
        self.__store_datas()
        dirname = os.path.dirname(__file__)
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.Popen(["python", os.path.join(dirname, "copy_to_distant.py"), self.__data_file_name], startupinfo=si)

        self.__stop_log()

    def run_copy(self):
        self.__start_log()
        self.__start_thread_log()
        self.__generate_ranged_cache_dest()
        self.__copy()
        self.__footer_log()
        self.__stop_log()
