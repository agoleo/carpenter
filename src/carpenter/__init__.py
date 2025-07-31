#!/bin/python3

import os
import logging
import sys
import argparse
import traceback
import glob
import json
import pathlib
import subprocess
from datetime import datetime
from pathlib import Path

import yaml

class Builder:

    def __init__(self, path, build_path=None, dependencies=None):

        self.path = path
        self.src_build_path = build_path

        self.curr_path = pathlib.Path(path).resolve()
        self.curr_id = pathlib.Path(self.curr_path).name

        if build_path:
            self.build_path = os.path.join(self.src_build_path, self.curr_id)
        else:
            self.build_path = os.path.join(self.curr_path, ".build/")

        self.build_path = pathlib.Path(self.build_path).resolve()
        self.out_dir = os.path.join(self.build_path, "out/")
        self.data_file = os.path.join(self.build_path, f"data.json")
        self.build_manifest_file = os.path.join(self.curr_path, f"carpenter.yaml")

        with open(self.build_manifest_file, "r") as f:
            self.build_manifest = yaml.safe_load(f.read())

        self.data = {
        }

        os.system(f"mkdir -p {self.out_dir}/")
        os.system(f"mkdir -p {self.build_path}/")
        self.load_data()

        self.dry_run = False

        self.dependencies = dependencies.copy() if dependencies is not None else {}


    def check_changed(self,
                      path,
                      exclude_folders=None,
                      exclude_globs=None):

        lst = list()

        with os.scandir(path) as it:
            for entry in it:
                if exclude_folders is None or entry.name not in exclude_folders:
                    lst += list(Path(entry).rglob('*')) + [os.path.join(path, entry.name), ]


        if exclude_globs:
            for exclude_glob in exclude_globs:
                for p in Path(path).rglob(exclude_glob):
                    if p in lst:
                        lst.remove(p)

        dt = None
        for path in lst:
            try:
                dm = datetime.fromtimestamp(os.path.getmtime(path))
                if dt is None or dm > dt:
                    dt = dm
            except:
                logging.info(f"failed to retrieve date for file {path}")

        return dt


    def save_data(self):

        try:
            with open(self.data_file, "w") as f:
                f.write(json.dumps(self.data, sort_keys=True, indent=4))
        except:
            logging.error("unable to save to data file")
            traceback.print_exc(file=sys.stderr)

    def load_data(self):

        try:
            with open(self.data_file, "r") as f:
                self.data = json.load(f)
        except:
            logging.error("unable to load data file, maybe cleaned environment")
            return

    def clear(self):

        logging.info("Cleaning up working directory")
        os.system(f"rm -f -R {self.build_path}/*")

    def build(self) -> int | None:
    
        newer_comp_dt = None
      
        if self.build_manifest.get('components'):
            for component in self.build_manifest['components']:
                comp_build = Builder(path=os.path.join(self.curr_path, component),
                                     build_path=self.src_build_path,
                                     dependencies=self.dependencies)

                self.dependencies[comp_build.curr_id] = comp_build

                try:
                    comp_build.build()
                except:
                    logging.error(f'failed to build component {component}')
                    raise

                dt_comp = comp_build.check_changed(os.path.join(comp_build.build_path))
                logging.info(f"build date for component {component}: {dt_comp}")
                if newer_comp_dt is None or dt_comp > newer_comp_dt:
                    newer_comp_dt = dt_comp

        build_retcode = self.data.get('build_retcode')
        new_dt = self.check_changed(self.curr_path, ['.git', '.build', 'dist'])

        logging.info(f'last build retcode={build_retcode}')

        if build_retcode is not None and build_retcode <= 0:
            logging.info('already build, check if something changed')
            build_date = datetime.fromisoformat(self.data.get('build_date'))
            logging.info(f'build_date={build_date}, new_dt={new_dt}')
            if new_dt == build_date:
                if not newer_comp_dt or datetime.fromisoformat(self.data.get('build_date')) > newer_comp_dt:
                    logging.info('nothing changed')
                    return
                logging.info('nothing changed, but components changed')

        self.data['build_retcode'] = None
        self.save_data()

        try:
            if self.build_manifest.get('build-script') is not None:
                build_script = self.build_manifest['build-script']
            else:
                build_script = 'build.sh'

            env = os.environ.copy()
            env['BUILD_PATH'] = self.build_path
            env['SCRIPT_PATH'] = self.curr_path
            env['OUT_PATH'] = self.out_dir

            build_retcode = self._execute(
                os.path.join(self.curr_path, "build.sh"),
                raise_on_error=True,
                env=env)

        finally:
            self.data['build_retcode'] = build_retcode
            self.data['build_date'] = new_dt.isoformat()

        self.save_data()


    def _get_script(self, cmd):

        inner_case = "".join(f'''
            "{cid}")
                echo {c.build_path};;
        ''' for (cid, c) in self.dependencies.items())

        script = f'''
        set -e
        echo $PATH
        get_build_path() {{
            case $1 in
                {inner_case}
                *)
                    echo component $1 not valid
                    exit 10
            esac
        }}
        source {cmd}
        '''

        return script

    def _execute(self, cmd, chdir=None, raise_on_error=True, env=None):
        logging.info(f"execute {cmd}")
        if self.dry_run:
            raise RuntimeError(f"cmd {cmd} failed being a dry run")
        
        if chdir is not None:
            os.chdir(chdir)

        try:

            cmd = ['bash', '-c', self._get_script(cmd)]

            process = subprocess.Popen(
               cmd,
               stdout=subprocess.PIPE,
               stderr=subprocess.STDOUT,
               env=env)

            output = ""

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                output += line.decode()
                print("*** " + line.decode(), end='')
                
            ret = process.returncode

            # logging.info(f"output from script: \n{output}")


        except FileNotFoundError as e:
            logging.warning(str(e))
            ret = 1


        if chdir is not None:
            os.chdir(self.curr_path)

        if ret > 0 and raise_on_error:
            raise RuntimeError(f"cmd {cmd} failed with return value {ret}")

        return ret


def main():
    logging.basicConfig(
        stream=sys.stderr, level="DEBUG",
        format="[%(asctime)s]%(levelname)s %(funcName)s() "
                "%(filename)s:%(lineno)d %(message)s")

    parser = argparse.ArgumentParser(
        prog="carpenter",
        description="a very minimalist build system",
        epilog="",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-o', "--option", dest="options", action='append',
                        help="option, passed as env variable to build scripts")

    parser.add_argument("--build-path", dest="build_path", required=False,
                        help="path used as cache for building")

    parser.add_argument("action", help="clear / build")
    parser.add_argument("path", help="folder of the component to build")

    args = parser.parse_args()

    builder = Builder(path=args.path, build_path=args.build_path)

    if args.action == 'clear':

        builder.clear()

    elif args.action == 'build':

        builder.build()

    else:

        logging.error("wrong action. Nothing to do")


    logging.debug(f"updated build data: {builder.data}")

