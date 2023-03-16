# TemplateNoUI Tool

> TemplateNoUI is a tool to ...

## How to install

You will need some files that several Illogic tools need. You can get them via this link :
https://github.com/Illogicstudios/common

You must specify the correct path of the installation folder and of the Arnold SDK in the ```template_main.py``` file :
```python
if __name__ == '__main__':
    # TODO specify the right path
    install_dir = 'PATH/TO/file_collector_ranch_sender'
    arnold_sdk_dir = "OTHER/PATHTO/Arnold-7.1.4.1-windows"
    # [...]
```

You must also specify the same paths in ```template_copy_to_distant.py``` file :
```python
# TODO specify the right path
install_dir = 'PATH/TO/file_collector_ranch_sender'
arnold_sdk_dir = "OTHER/PATHTO/Arnold-7.1.4.1-windows"
```

---

## Feature

<div align="center">
  <span>
    <img src="https://user-images.githubusercontent.com/94440879/216031775-d9ea680f-9a91-4f19-bc4c-6dd7fae4aa6b.png" width=50%>
  </span>
  <p weight="bold">Caption</p>
  <br/>
</div>

[...]