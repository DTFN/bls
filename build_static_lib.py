#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
from os.path import join
import subprocess
import glob
from subprocess import run

BASE_PATH = os.path.abspath('.')

ar_bin = "/usr/bin/ar"
libstdcpp_name = "libstdc++.a"
libblsmcl_name = "libblsmcl.a"


def join_path(*path_tuple):
    path_list = list(path_tuple)
    if len(path_list) > 1:
        return os.path.realpath(os.path.join(path_list[0], *path_list[1:]))
    if len(path_list) == 1:
        return os.path.realpath(os.path.join(path_list[0]))

bls_source_dir = BASE_PATH
mcl_source_dir = join_path(BASE_PATH, "../mcl")

bls_lib_dir = join_path(BASE_PATH, "./lib")
bls384_lib = join_path(BASE_PATH, "./lib/libbls384.a")
mcl_lib = join_path(BASE_PATH, "../mcl/lib/libmcl.a")
static_lib_dir = join_path(BASE_PATH, "./static_lib")
libblsmcl = join_path(static_lib_dir, libblsmcl_name)


def check_file_extsis(filepath):
    try:
        os.stat(filepath)
    except Exception as e:
        return e
    return True


def run_program(file_name, args, cwd=None, env=None, shell=False):
    cmd_list = []
    cmd_list.append(file_name)
    if isinstance(args, list):
        for arg in args:
            cmd_list.append(arg)
    else:
        raise TypeError("args must be list type")

    if cwd != None:
        if not isinstance(cwd, str):
            raise TypeError("cwd must be string type")

    if env != None:
        if not isinstance(env, dict):
            raise TypeError("env must be dict type")
        for key in env:
            value = env.get(key)
            os.environ[key] = value

    p = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=os.environ, shell=shell)
    p.wait()
    return p.returncode, p.stdout.read(), p.stderr.read()


# 编译bls和mcl源码
def make_bls_mcl_lib():
    print("开始编译 mcl 库...")

    return_code, _, stderr = run_program("make", ["clean"], cwd=mcl_source_dir, shell=False)
    if return_code != 0:
        print("编译 mcl 库失败：{0}".format(stderr.decode()))
        return

    return_code, _, stderr = run_program("make", ["-j4"], cwd=mcl_source_dir, env={"MCL_USE_GMP":"0"})
    if return_code != 0:
        print("编译 mcl 库失败：{0}".format(stderr.decode()))
        return
    
    print("编译 mcl 库完成.")
    print("开始编译 bls 库...")
    
    return_code, _, stderr = run_program("make", ["clean"], cwd=bls_source_dir, shell=False)
    if return_code != 0:
        print("编译 bls 库失败：{0}".format(stderr.decode()))
        return

    return_code, _, stderr = run_program("make", ["-j4"], cwd=bls_source_dir, env={"MCL_USE_GMP":"0"})
    if return_code != 0:
        print("编译 bls 库失败：{0}".format(stderr.decode()))
        return
    
    print("编译 bls 库完成.")


# 生成静态链接库
def generate_static_bls_mcl_lib():
    exists = check_file_extsis(static_lib_dir)
    if isinstance(exists, Exception):
        return_code, _, staderr  = run_program("mkdir", [static_lib_dir])
        if return_code != 0:
            print("创建 {0} 文件夹失败: {1}".format(static_lib_dir, staderr.decode()))
            return
    

    exists = check_file_extsis(ar_bin)
    if isinstance(exists, Exception):
        print("ar程序不存在，请检查")

    exists = check_file_extsis(bls384_lib)
    if isinstance(exists, Exception):
        print("libbls384.a不存在，请先编译bls库.")
        return

    exists = check_file_extsis(mcl_lib)
    if isinstance(exists, Exception):
        print("libmcl.a不存在，请先编译mcl库.")
        return

    
    return_code, _, stderr = run_program(ar_bin, ["x", bls384_lib], cwd=static_lib_dir)
    if return_code != 0:
        print("无法打开 {0}: {1}".format(bls384_lib, stderr.decode()))
        return

    return_code, _, _ = run_program(ar_bin, ["x", mcl_lib], cwd=static_lib_dir)
    if return_code != 0:
        print("无法打开 {0}".format(mcl_lib))
        return
    
    _, stdout, _ = run_program("gcc", ["--print-file-name", libstdcpp_name])
    path = stdout.decode()
    stdcpp_path = path.replace('\n', '')
    exists = check_file_extsis(stdcpp_path)
    if isinstance(exists, Exception):
        print("无法找到 {0}".format(libstdcpp_name))
        return
    
    return_code, _, _ = run_program(ar_bin, ["x", stdcpp_path], cwd=static_lib_dir)
    if return_code != 0:
        print("无法打开 {0}".format(mcl_lib))
        return
    
    target_files = glob.glob(os.path.join(static_lib_dir, "*.o"))
    if len(target_files) == 0:
        print("目录 [{0}] 找不到目标文件.".format(static_lib_dir))
        return
    
    return_code, _, stderr = run_program(ar_bin, ["rc", libblsmcl, *target_files], cwd=static_lib_dir)
    if return_code != 0:
        print("无法创建 {0}: {1}".format(libblsmcl, stderr.decode()))
        return
    
    return_code, _, stderr = run_program("/bin/cp", [libblsmcl, bls_lib_dir])
    if return_code != 0:
        print("复制文件失败 {0}: {1}".format(libblsmcl, stderr.decode()))
        return

    bls_lib_dir_blsmcl = join_path(bls_lib_dir, libblsmcl_name)
    libblsmcl_stat = os.stat(bls_lib_dir_blsmcl)
    file_size = libblsmcl_stat.st_size
    print("创建静态链接库: [{0}] 大小: [{1}] MBytes.".format(bls_lib_dir_blsmcl, round(file_size/1024/1024.0, 2)))


if __name__ == "__main__":
    make_bls_mcl_lib()
    generate_static_bls_mcl_lib()