# Introduction

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
- `builder.sh`: the script that is executed

# Manifest description

```
name: example
version: 0.1
components:
  - ../component-example
exclude_date_check:
  - file_that_changes
```
