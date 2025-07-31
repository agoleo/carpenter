# Introduction

Please note, this project is a WIP at very early stage and it is not
suitable for real cases yet since it lacks documentation and it is subjected
to major changes.

Carpenter allows to build a project with different "components".
Each component is located in a folder and shall contain the file build.yaml,
we call it the 'build manifest'.
If a component A needs the built files of another component B, B is inserted
in the list "components" of A's manifest.
Each time a component is built, a subfolder .build is created and the file
build.sh is called (unless otherwise stated in the build). If no file has been
modified, the build is skipped the next time.

A carpenter is one of the skills needed to build a house. It's also the surname
of a film director I love very much.


# Usage

Each component should have two files:

- `carpenter.yaml`: the component's manifest file (see manifest description)
- `build.sh`: the script that is executed

# Manifest description

```
name: example
version: 0.1
components:
  - ../component-example
exclude_date_check:
  - file_that_changes
```

# Build scripts

The build script is a bash script located into root folder of the component and
called `build.sh`.
The following elements are defined:
 - environment variable `BUILD_PATH`: the build cache directory
 - environment variable `CURR_PATH`: the directory where the build script is located
 - environment variable `OUT_PATH`: the build out directory
 - function `get_build_path()`, to retrieve the build cache directory of a dependency/
   component.
 - function `get_out_path()`, to retrieve the build out directory of a dependency/
   component.
