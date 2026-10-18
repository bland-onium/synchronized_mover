**ALERT** Tested only on linux. Use at Windows by your aware

# synchronized_mover
This script are used to move data from one place to another looking on structure of third (like a robocopy or rsync but it mimics data structure of another source). Uses python and included libraries.
Now has 90% accuracy. with errors i'm working...

### HOW IT WORKS
Usage: python3 syncmover -v -d -y /.../home_directory /.../mirror_directory /.../destination_directory
Program scans home and mirroring directories, builds their file maps and begin to transfer.
Due transfering each element goes througs predictive check (before move) and "aftercheck" (after move)
About errors and unknown mistakes program tells after all
Usually, good move is running rsync from mirroring directory cause errors mean that part of structure were lost



It was hard to describe and imagine but i did it.
Code has more than 10 ways of checking files
AI used only as library - it is stupid to correctly realise this logic

futere tasks:
- [x] add commands and flags
- [x] add flag -d for debugging (deeper than -v)
- [x] add flag -v for verbose 
- [x] add arguments for script
- [x] add autofilling
- [ ] add GUI
- [ ] add erroring automove
- [ ] improve erroring mechanics
- [x] improve map-building module
- [x] rewrite move module to let it at first print ways of moving files
- [x] add flag -y for autoagreement
- [x] add automatical terminal wrapping
