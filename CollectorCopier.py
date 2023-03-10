import shutil
import os
import threading
import re
import time
from pymel.all import *
from queue import Queue

import sys

sys.path.append(r"R:\pipeline\networkInstall\arnold\Arnold-7.1.4.1-windows")
from arnold import *

from utils import *

# ######################################################################################################################

_RANCH_SERVER = "RANCH-126"
_RANCH_FOLDER = "ranch_cache"
_MAX_NB_THREADs = 256

# ######################################################################################################################

# 18 + Length of longer message possible (here : "File more recent exists")
_LENGTH_PADDING = 18 + 23
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
        self.__scene_found = False
        self.__scene_name = ""
        self.__file_logs_name =""
        self.__scene_datas = {}
        self.__reinit_copy_attributes()
        self.__datas_lock = threading.Lock()
        self.__progress_lock = threading.Lock()
        self.__output_queue = Queue()

    # Init some attributes for the copy and logs
    def __reinit_copy_attributes(self):
        self.__total_file_size = 0
        self.__current_file_size = 0
        self.__total_file_nb = 0
        self.__current_file_nb = 0
        self.__current_data_index = 0
        self.__datas_length = len(self.__datas)
        self.__max_length_path = 0

    # Output the logs in a file and text
    def __thread_output(self):
        while True:
            msg = self.__output_queue.get()
            f = open(self.__file_logs_name, "a")
            f.write(msg + "\n")
            f.close()
            # TODO remove
            print(msg, flush=True)
            time.sleep(0.01)

    # Setup the thread output that uses a queue
    def __setup_output_queue(self):
        th = threading.Thread(target=self.__thread_output, daemon=True)
        th.start()

    # Copy with datas to Ranch
    def __copy_from_data(self, data):
        count_file_str_length = 2 * len(str(self.__datas_length)) + 1
        str_length = self.__max_length_path + count_file_str_length + _LENGTH_PADDING
        os.makedirs(data['folder_dest'], exist_ok=True)
        path_src = data["src"]
        path_dest = data["dest"]

        # Check whether the file need to by copied
        do_copy = True
        if os.path.exists(path_dest):
            mtime_src = os.path.getmtime(path_src)
            mtime_dest = os.path.getmtime(path_dest)
            if mtime_src >= mtime_dest:
                do_copy = False

        if do_copy:
            # Copy
            shutil.copy2(path_src, path_dest)

        # Output Logs
        with self.__progress_lock:
            self.__current_file_size += data["size"]
            self.__current_file_nb += 1
            percent_copied = round(self.__current_file_size / self.__total_file_size * 100, 2)
            str_percent = str(percent_copied).rjust(5) + "%"
            str_file_count = (str(self.__current_file_nb) + "/" + str(self.__total_file_nb)).rjust(
                count_file_str_length)
            msg = "Copy On RANCH of" if do_copy else "File more recent exists"
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
        if self.__scene_found:
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
            th = threading.Thread(target=self.__thread_copy_file, daemon=True)
            threads.append(th)
            th.start()
        # Join All Threads
        for th in threads:
            th.join()

        # At the end when all files have been copied we can copy the scene
        with self.__datas_lock:
            if self.__scene_found:
                self.__copy_from_data(self.__scene_datas)

        with self.__progress_lock:
            msg = "+- Copy On RANCH Finished "

            self.__output_queue.put(
                msg.ljust(self.__max_length_path + count_file_str_length + _LENGTH_PADDING, "-") + "+")

    # Retrieve all the paths used in Maya Scene
    def __retrieve_paths_in_maya(self):
        self.__output_queue.put("\n+- Start retrieve all the paths in Maya -----")
        list_dir = filePathEditor(query=True, listDirectories="")
        nb_found = 0
        if list_dir is not None:
            for directory in list_dir:
                list_file_elem = filePathEditor(query=True, listFiles=directory)
                for fil in list_file_elem:
                    path = os.path.join(directory, fil)
                    if path not in self.__datas and os.path.exists(path):
                        self.__output_queue.put("| Filepath found : " + path)
                        self.__datas.append(path)
                        nb_found += 1
        self.__output_queue.put("+- End retrieve all the paths in Maya [" + str(nb_found) + "]-----")

    # Retrieve all the paths used in dso of StandIn in Scene
    def __retrieve_paths_in_ass(self):
        self.__output_queue.put("\n+- Start retrieve all the paths in ASS files -----")
        list_standin = ls(type='aiStandIn')
        AiBegin(AI_SESSION_BATCH)
        AiMsgSetConsoleFlags(AI_LOG_ALL)
        nb_found = 0
        # Iterate through StandIn
        for standin in list_standin:
            ass_paths_standin = []
            dso = standin.dso.get()
            texture_search_paths = []

            AiASSLoad(dso)
            self.__output_queue.put("| Search in " + standin + " (" + dso + ")")
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
                        if len(filename) > 0 and filename not in ass_paths_standin:
                            ass_paths_standin.append(filename)
                    # IF OPTIONS Retrieve the texture search path
                    elif is_options and len(texture_search_paths) == 0:
                        texture_search_paths = AiNodeGetStr(node, "texture_searchpath")

            if len(ass_paths_standin) > 0:
                for base_path in texture_search_paths.split(";"):
                    # If all file processed stop the search
                    if len(ass_paths_standin) == 0:
                        break

                    # Try to find if the path is a reference to an env var
                    match = re.match(r"^\[(\w+)]$", base_path)
                    if match:
                        env_var_name = match.group(1)
                        env_var = os.getenv(env_var_name)
                        if env_var:
                            base_path = env_var

                    # For each file try to base_path, If exists remove the file from the list to processed
                    to_remove = []
                    for ass_path in ass_paths_standin:
                        ass_complete_path = os.path.join(base_path, ass_path)
                        if os.path.exists(ass_complete_path):
                            if ass_complete_path not in self.__datas:
                                self.__datas.append(ass_complete_path)
                                self.__output_queue.put("|    +----> " + ass_complete_path)
                                nb_found += 1
                            to_remove.append(ass_path)
                    if len(to_remove) > 0:
                        for ass_to_remove in to_remove:
                            ass_paths_standin.remove(ass_to_remove)

            AiNodeIteratorDestroy(iterator)
        AiEnd()
        self.__output_queue.put("+- End retrieve all the paths in ASS files [" + str(nb_found) + "]-----")

    # Generate all the datas from the file path
    def __generate_ranged_cache_dest(self):
        ranged_cache_paths = []
        for path in self.__datas:
            data = CollectorCopier.__generate_data_for_path(path)
            if data is not None:
                ranged_cache_paths.append(data)
        self.__datas = ranged_cache_paths
        if self.__scene_found and os.path.exists(self.__scene_name):
            scene_datas = CollectorCopier.__generate_data_for_path(self.__scene_name)
            if scene_datas is not None:
                self.__scene_datas = scene_datas

    # Collect and Copy in a thread
    def __thread_run(self):
        self.__header_logs()
        self.__setup_output_queue()
        self.__retrieve_paths_in_maya()
        self.__retrieve_paths_in_ass()
        self.__generate_ranged_cache_dest()
        self.__copy()
        self.__footer_logs()

    # Generate the logs file name and the Header
    def __header_logs(self):
        if self.__scene_found:
            self.__file_logs_name = os.path.join(os.path.dirname(self.__scene_name),"collector_copier_logs")
            padding_length = (_LENGTH_HEADER_FOOTER-21)//2
            header = padding_length*"#"+" "+time.strftime("%Y-%m-%d %H:%M:%S")+" "+padding_length*"#"
            self.__output_queue.put(header)

    # Generate the Footer
    def __footer_logs(self):
        if self.__scene_found:
            footer = _LENGTH_HEADER_FOOTER*"#"
            self.__output_queue.put(footer)

    # Run Collector and Copier to Ranch
    def run(self):
        self.__datas.clear()
        self.__scene_name = sceneName()
        self.__scene_found = len(self.__scene_name) > 0
        th = threading.Thread(target=self.__thread_run, daemon=True)
        th.start()
