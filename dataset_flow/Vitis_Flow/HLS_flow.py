import os, sys, shutil
import subprocess
import numpy as np
from reg_parser import CodeText, parse_file, clear_by_all_strIdxRanges

# Function to generate TCL file content
def generate_tcl_file(module_name):
    return f"""open_project {module_name}
set_top {module_name}

add_files ./{module_name}.cpp

open_solution \"solution1\" -flow_target vivado
set_part {{xczu9eg-ffvb1156-2-e}}
create_clock -period 10 -name default

csynth_design

exit
"""

def write_toplevel_file(func_name, toplevel_folder_path, toplevel_file_content):
    os.makedirs(toplevel_folder_path, exist_ok=True)
    with open(os.path.join(toplevel_folder_path, f"{func_name}.cpp"), 'w') as f:
        f.write(toplevel_file_content)
    tcl_file = os.path.join(toplevel_folder_path, f"{func_name}.tcl")
    with open(tcl_file, "w") as tcl:
        tcl.write(generate_tcl_file(module_name=func_name))


def copy_dependency_files(src_file_path, toplevel_folder_path, src_repo_path, repo_parse_dict, 
        dependency_folder_name="toplevel_imports", is_toplevel=False):
    # copy dependency files of the file at src_file_path (all those under src_repo_path) 
    # to folder dependency_folder_name under toplevel_folder_path, replicate directories 
    # in src_repo_path, return if no dependencies found. All paths are abspaths.
    # copy current file at src_file_path if this is not toplevel
    file_from_repo_relpath = os.path.relpath(src_file_path, src_repo_path)
    print(f"in code dependency for {src_file_path}")
    if not is_toplevel:
        if not os.path.isfile(src_file_path):
            return
        dependency_folder_path = os.path.join(toplevel_folder_path, dependency_folder_name)
        target_file_path = os.path.abspath(
            os.path.join(dependency_folder_path, file_from_repo_relpath) )
        if os.path.isfile(target_file_path):
            return
        os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
        print(f"made a directory at {os.path.dirname(target_file_path)}")
        shutil.copyfile(src_file_path, target_file_path)
    # copy all dependencies of this file
    if src_file_path not in repo_parse_dict.keys():
        repo_parse_dict[src_file_path] = parse_file(src_file_path)
    src_file_codetexts = repo_parse_dict[src_file_path]
    dependency_file_paths = [ct.name for ct in src_file_codetexts if ct.type == "include"]
    dependency_file_paths = [os.path.join(os.path.dirname(src_file_path), p) for p in dependency_file_paths]
    dependency_file_paths = [os.path.abspath(p) for p in dependency_file_paths]
    # if .hpp is copied, also include .cpp; if .h is copied, also include .c.
    for dfpath in dependency_file_paths:
        if os.path.splitext(dfpath)[1] == ".h" and os.path.isfile(os.path.splitext(dfpath)[0]+".c"):
            dependency_file_paths.append(os.path.splitext(dfpath)[0]+".c")
        if os.path.splitext(dfpath)[1] == ".hpp" and os.path.isfile(os.path.splitext(dfpath)[0]+".cpp"):
            dependency_file_paths.append(os.path.splitext(dfpath)[0]+".cpp")
    # if os.path.splitext(file_from_repo_relpath) == ".h" and :
    for dfpath in dependency_file_paths:
        copy_dependency_files(src_file_path=dfpath, toplevel_folder_path=toplevel_folder_path, 
            src_repo_path=src_repo_path, repo_parse_dict=repo_parse_dict, 
            dependency_folder_name=dependency_folder_name, is_toplevel=False)


def write_project(func_name, toplevel_folder_path, src_repo_path, func_src_file_path, repo_parse_dict):
    # repo_parse_dict: {src_code_file_abspath: list_of_all_this_files_CodeTexts}
    dependency_folder_name = "top_level_module"
    # write all dependency files of toplevel
    copy_dependency_files(src_file_path=func_src_file_path, toplevel_folder_path=toplevel_folder_path,
        src_repo_path=src_repo_path, repo_parse_dict=repo_parse_dict, 
        dependency_folder_name=dependency_folder_name, is_toplevel=True)
    # process toplevel file content
    with open(func_src_file_path, 'r') as f:
        toplevel_file_content = f.read()
    if func_src_file_path not in repo_parse_dict.keys():
        repo_parse_dict[func_src_file_path] = parse_file(func_src_file_path)
    toplevel_cts = repo_parse_dict[func_src_file_path]
    func_ct_idx = [i for i,ct in enumerate(toplevel_cts) if ct.name == func_name][0]    # only match the first one if there are duplicated function names
    func_ct = toplevel_cts[func_ct_idx]
    # update include lines
    include_cts = [ct for ct in toplevel_cts if ct.type == "include"]
    toplevel_file_content = clear_by_all_strIdxRanges(text=toplevel_file_content, all_strIdxRanges=[ct.strIdxRange for ct in include_cts])
    toplevel_prefixes_list = []
    for ct in include_cts:
        toplevel_prefixes_list.append('#include "'+ os.path.join(
            dependency_folder_name, os.path.relpath(os.path.join(os.path.dirname(func_src_file_path), ct.name), src_repo_path)
        )+'"')
        # if .hpp is copied, also include .cpp; if .h is copied, also include .c.
        _candidate_c_path = os.path.join(os.path.dirname(func_src_file_path), ct.name[:-2]+".c")
        if os.path.splitext(ct.name)[1] == ".h" and os.path.isfile(_candidate_c_path) and _candidate_c_path != func_src_file_path:
            toplevel_prefixes_list.append('#include "'+ os.path.join(
                dependency_folder_name, os.path.relpath(_candidate_c_path, src_repo_path)
            )+'"')
        _candidate_cpp_path = os.path.join(os.path.dirname(func_src_file_path), ct.name[:-4]+".cpp")
        if os.path.splitext(ct.name)[1] == ".hpp" and os.path.isfile(_candidate_cpp_path):
            toplevel_prefixes_list.append('#include "'+ os.path.join(
                dependency_folder_name, os.path.relpath(_candidate_cpp_path, src_repo_path)
            )+'"')
    toplevel_prefixes = "\n".join(toplevel_prefixes_list) + "\n"
    # update template content if needed
    if "template" in func_ct.optionDict.keys():
        _tmpl = func_ct.optionDict['template']
        new_tmpl_str = reformat_template(tmpl_codetext=_tmpl)    #TODO, automate correct value candidates if needed
        _pre_tmpl_str  = toplevel_file_content[:_tmpl.strIdxRange[0]]
        _post_tmpl_str = toplevel_file_content[_tmpl.strIdxRange[1]:] 
        toplevel_file_content = _pre_tmpl_str + new_tmpl_str + "\n" + _post_tmpl_str
    # generate correct top_level_file_content
    toplevel_file_content = toplevel_prefixes + toplevel_file_content
    write_toplevel_file(func_name=func_name, toplevel_folder_path=toplevel_folder_path, 
        toplevel_file_content=toplevel_file_content)


def reformat_template(tmpl_codetext, numerical_candidates=[8,16,32,64], 
        # type_candidates=["ap_int<4>","ap_int<8>","ap_int<16>","ap_int<32>","ap_int<64>","ap_int<128>"]
        type_candidates=["ap_int<16>"]
        ):
    # reformat original design's template and convert them to const and/or typedef statements
    # since Vitis/Vivado HLS does not accept top-level with templates.
    _text = tmpl_codetext.text
    _text = _text[_text.find("template"):][len("template"):]
    _text = _text[(_text.find("<")+len("<")):_text.rfind(">")].strip()
    _vars = [v.strip() for v in _text.split(",")]
    ret_vars = []
    for v in _vars:
        if "=" in v:
            _partial_vs = v.split(" ")
            if "typename" in _partial_vs:
                _def_v_str = " ".join(_partial_vs[(_partial_vs.index("typename")+1):])
                _def_v_type, _def_v_value = _def_v_str.split("=")
                _def_v_type, _def_v_value = _def_v_type.strip(), _def_v_value.strip()
                ret_vars.append("typedef " + _def_v_value + "=" + _def_v_type + ";")
            else:
                ret_vars.append("const " + v + ";")
        else:
            _partial_vs = v.split(" ")
            if "typename" in _partial_vs:
                _def_v_str = " ".join(_partial_vs[(_partial_vs.index("typename")+1):])
                ret_vars.append("typedef " + str(np.random.choice(type_candidates)) + " " + _def_v_str + ";")
            else:
                ret_vars.append("const "+ v + "=" + str(np.random.choice(numerical_candidates)) + ";")
    return "\n".join(ret_vars)


def run_one_hls_design(tcl_path):
    tcl_folder_path = os.path.dirname(tcl_path)
    tcl_file_name = os.path.basename(tcl_path)

    log_file_path = os.path.join(tcl_folder_path, f"{tcl_file_name[:-4]}_hls.log")
    
    try:
        # Make sure the directory exists
        if not os.path.exists(tcl_folder_path):
            raise FileNotFoundError(f"Directory {tcl_folder_path} does not exist.")
        
        vitis_path = ""
        
        subprocess.run(['bash', '-c', vitis_path])

        # Run the HLS design process
        hls_run_result = subprocess.run(
            f'vitis_hls -f {tcl_file_name}',
            shell=True,
            capture_output=True,
            cwd=tcl_folder_path
        )

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    return hls_run_result