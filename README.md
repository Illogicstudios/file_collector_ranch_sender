# File Collector Ranch Sender

> File Collector Ranch Sender is a tool to copy all file that are in a Maya scene on a distant server

## How to install

You will need some files that several Illogic tools need. You can get them via this link :
https://github.com/Illogicstudios/common

You must specify the correct path of the installation folder :
```python
if __name__ == '__main__':
    # TODO specify the right paths
    install_dir = 'PATH/TO/file_collector_ranch_sender'
    # [...]
```

You must also specify the same path in ```template_copy_to_distant.py``` file :
```python
# TODO specify the right paths
install_dir = 'PATH/TO/file_collector_ranch_sender'
```

Change some parameters in ```CollectorCopier.py``` file to copy the file where you want:
```python

# ######################################################################################################################

_RANCH_CACHE_FOLDER = "I:/ranch/ranch_cache"
_LOGS_FOLDER = "I:/ranch/logs"
_MAX_NB_THREADs = 32

_ASS_PATHS_FILE_EXTENSION = "paths"

# ######################################################################################################################
```

---

[//]: # (## Feature)

[//]: # ()
[//]: # (<div align="center">)

[//]: # (  <span>)

[//]: # (    <img src="https://user-images.githubusercontent.com/94440879/216031775-d9ea680f-9a91-4f19-bc4c-6dd7fae4aa6b.png" width=50%>)

[//]: # (  </span>)

[//]: # (  <p weight="bold">Caption</p>)

[//]: # (  <br/>)

[//]: # (</div>)

[//]: # ()
[//]: # ([...])