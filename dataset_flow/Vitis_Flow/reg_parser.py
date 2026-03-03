import os, re
from collections import namedtuple

CPP_KEYWORDS=[ "alignas", "alignof", "and", "and_eq", "asm", "atomic_cancel", "atomic_commit", "atomic_noexcept", "auto", "bitand", "bitor", "bool", "break", "case", "catch", "char", "char8_t", "char16_t", "char32_t", "class", "compl", "concept", "const", "consteval", "constexpr", "constinit", "const_cast", "continue", "co_await", "co_return", "co_yield", "decltype", "default", "delete", "do", "double", "dynamic_cast", "else", "enum", "explicit", "export", "extern", "false", "float", "for", "friend", "goto", "if", "inline", "int", "long", "mutable", "namespace", "new", "noexcept", "not", "not_eq", "nullptr", "operator", "or", "or_eq", "private", "protected", "public", "reflexpr", "register", "reinterpret_cast", "requires", "return", "short", "signed", "sizeof", "static", "static_assert", "static_cast", "struct", "switch", "synchronized", "template", "this", "thread_local", "throw", "true", "try", "typedef", "typeid", "typename", "union", "unsigned", "using", "virtual", "void", "volatile", "wchar_t", "while", "xor", "xor_eq"]

CodeText = namedtuple('CodeText', [
    'type', # code block type like function, include, define, etc.
    'name', # code block name like the name of this function or file in include.
    'text', # text content of this code block.
    'filePath',    # path of the source file where code block is extracted.
    'startLine',   # start line number in the source file, starts from 1.
    'endLine',     # non-inclusive end line in the source file.
    'strIdxRange', # tuple of (strTextInclusiveStartIdx, strTextExclusiveEndIdx), temperary values only.
    'optionDict'   # optional dict for custom values.
])

IGNORE_INCLUDES = ["hls_stream.h", "ap_axi_sdata.h"]


def _merge_overlap(arr):
    # ref: https://www.geeksforgeeks.org/merging-intervals/
    n = len(arr)
    arr.sort()
    res = []
    # Checking for all possible overlaps
    for i in range(n):
        start = arr[i][0]
        end = arr[i][1]
        # Skipping already merged intervals
        if res and res[-1][1] >= end:
            continue
        # Find the end of the merged range
        for j in range(i + 1, n):
            if arr[j][0] <= end:
                end = max(end, arr[j][1])
        res.append((start, end))
    return res

def clear_by_strIdxRange(text, strIdxRange):
    assert strIdxRange[1] <= len(text), print("strIdxRange:", strIdxRange, "has ending idx beyond text length of", len(text))
    # text = text[:strIdxRange[0]] + "\n" * text[strIdxRange[0]:strIdxRange[1]].count("\n") + text[strIdxRange[1]:]
    ret_text = text[:strIdxRange[0]] + re.sub(r"[^\n]", r" ", text[strIdxRange[0]:strIdxRange[1]]) + text[strIdxRange[1]:]
    assert len(ret_text) == len(text)
    return ret_text

def clear_by_all_strIdxRanges(text, all_strIdxRanges):
    target_ranges = _merge_overlap(all_strIdxRanges)
    for start_idx, end_idx in target_ranges:
        text = clear_by_strIdxRange(text, strIdxRange=(start_idx, end_idx))
    return text

def clear_comments(text):
    # text: a string of cpp code
    # replace all single-line comments followed by newline with newline-only
    oneline_pattern = re.compile(r"//.*?\n", re.S)
    all_strIdxRanges = [(match.start(), match.end()) for match in oneline_pattern.finditer(text)]
    text = clear_by_all_strIdxRanges(text=text, all_strIdxRanges=all_strIdxRanges)
    # replace all multi-line comments with equal number of '\n'
    multiline_pattern = re.compile(r"/\*.*?\*/", re.S)
    all_strIdxRanges = [(match.start(), match.end()) for match in multiline_pattern.finditer(text)]
    text = clear_by_all_strIdxRanges(text=text, all_strIdxRanges=all_strIdxRanges)
    return text

def clear_ifndefs(text):
    # text: a string of cpp code
    # replace all #ifndef XXX` followed by newline with equal length of white spaces and newlines
    ifndef_pattern = re.compile(r"\s*#ifndef\s*.*?\n", re.MULTILINE)
    all_strIdxRanges = [(match.start(), match.end()) for match in ifndef_pattern.finditer(text)]
    text = clear_by_all_strIdxRanges(text=text, all_strIdxRanges=all_strIdxRanges)
    # replace all `#endif` followed by newline with equal length of white spaces and newline
    endif_pattern = re.compile(r"\s*#endif\s*\n", re.MULTILINE)
    all_strIdxRanges = [(match.start(), match.end()) for match in endif_pattern.finditer(text)]
    text = clear_by_all_strIdxRanges(text=text, all_strIdxRanges=all_strIdxRanges)
    return text

def clear_strings(text):
    # text: a string of C++ code possibly containing strings
    # replace all strings ("XXX", or 'X') with equal length of white spaces and newlines
    
    cur_string_char = None  # could be ", or ', or None
    cur_range_start = None
    all_strIdxRanges = []
    
    i = 0
    while i < len(text):
        char = text[i]
        
        if char == "'" and (i == 0 or text[i - 1] != '\\'):  # single quote, not part of an escape sequence (either at beginning ot not in comment)
            if cur_string_char is None:
                # Starting with a single quote
                cur_string_char = "'"
                cur_range_start = i
            elif cur_string_char == "'":
                # Ending with a single quote
                all_strIdxRanges.append((cur_range_start, i + 1))
                cur_string_char = None
                cur_range_start = None
        elif char == '"' and (i == 0 or text[i - 1] != '\\'):  # double quote, not part of an escape sequence
            if cur_string_char is None:
                # Starting with a double quote
                cur_string_char = '"'
                cur_range_start = i
            elif cur_string_char == '"':
                # Ending with a double quote
                all_strIdxRanges.append((cur_range_start, i + 1))
                cur_string_char = None
                cur_range_start = None
        
        i += 1
    
    # Assuming clear_by_all_strIdxRanges replaces the string ranges with white spaces/newlines
    text = clear_by_all_strIdxRanges(text, all_strIdxRanges)
    return text


def extract_includes(content, filePath=None):
    # content: C/C++ code string without comments
    include_pattern = re.compile(r'#include\s+"([^"]+)"', re.MULTILINE)
    ret_codetexts = []
    for match in include_pattern.finditer(content):
        include_path = match.group(1)
        start_line_offset = content[:match.start()].count("\n") + 1
        if include_path not in IGNORE_INCLUDES:
            ret_codetexts.append(CodeText(
                type = "include",
                name = include_path,
                text = content[match.start():match.end()].strip(),
                filePath    = filePath,
                startLine   = start_line_offset,
                endLine     = start_line_offset + 1,
                strIdxRange = (match.start(), match.end()),
                optionDict  = {}
            ))
    return ret_codetexts

def extract_constant_defines(content, filePath=None):
    # content: C/C++ code string without comments
    define_pattern = re.compile(r'#define\s+[^\n]+', re.MULTILINE)
    ret_codetexts = []
    for match in define_pattern.finditer(content):
        start_line_offset = content[:match.start()].count("\n") + 1
        splitted_statements = content[(match.start()+len("#define")):match.end()].split(" ")
        nontrivial_statements = [s.strip() for s in splitted_statements if s.strip() != ""]
        define_name = nontrivial_statements[0]
        ret_codetexts.append(CodeText(
            type = "define",
            name = define_name,
            text = content[match.start():match.end()].strip(),
            filePath    = filePath,
            startLine   = start_line_offset,
            endLine     = start_line_offset + 1,
            strIdxRange = (match.start(), match.end()),
            optionDict  = {"define_type": "one-line"}
        ))
    return ret_codetexts

def extract_expression_defines(content, filePath=None):
    # content: C/C++ code string without comments
    define_pattern = re.compile(r'#define\s+[^\s\(\)]+\s+\(', re.MULTILINE)
    define_steds = [(match.start(), match.end()) for match in define_pattern.finditer(content)]
    # extract defines by ()
    define_str_idx_ranges = []
    for i in range(len(define_steds)):
        cur_start = define_steds[i][1]
        cur_end = len(content)
        cur_bracket_balance = 1   # how many (s over )s
        for c in range(cur_start, cur_end):
            if content[c] == "(":
                cur_bracket_balance += 1
            elif content[c] ==")":
                cur_bracket_balance -= 1
                if cur_bracket_balance == 0:
                    break
        assert cur_bracket_balance == 0, print(cur_bracket_balance, cur_start, cur_end, content[cur_start:cur_end])
        define_start = define_steds[i][0]
        define_end = c + 1
        define_str_idx_ranges.append((define_start, define_end))
    define_contents = [content[define_str_idx_ranges[i][0]:define_str_idx_ranges[i][1]] for i in range(len(define_str_idx_ranges))]
    # format outputs
    ret_codetexts = []
    for i in range(len(define_str_idx_ranges)):
        cur_raw_text = define_contents[i]
        cur_text = cur_raw_text.strip()
        cur_name = cur_text[len("#define"):cur_text.find("(")].strip()
        start_line_offset = content[:define_str_idx_ranges[i][0]].count("\n") + 1
        end_line_offset = start_line_offset + cur_raw_text.count("\n") + 1
        ret_codetexts.append(CodeText(
            type = "define",
            name = cur_name,
            text = cur_text,
            filePath    = filePath,
            startLine   = start_line_offset,
            endLine     = end_line_offset,
            strIdxRange = define_str_idx_ranges[i],
            optionDict  = {"define_type": "multi-line-expression"}
        ))
    return ret_codetexts

def extract_defines(content, filePath=None):
    # content: C/C++ code string without comments
    ret_defines = []
    ret_defines.extend(extract_expression_defines(content=content, filePath=filePath))
    ret_defines.extend(extract_constant_defines(content=content, filePath=filePath))
    # TODO multi-line define with `\` character before newline is not supported yet, their names are extracted as 'one-line' now.
    # TODO: parametered expression defines like `#define EXPR(params) values` are not suppored yet.
    # ret_defines.extend(extract_paramed_expression_defines(content=content, filePath=filePath))
    return ret_defines


def extract_templates(content, filePath=None):
    # Function to replace match with equal number of newlines
    tmpl_pattern = re.compile(r'template\s*<', re.MULTILINE)
    tmpl_steds = [(match.start(), match.end()) for match in tmpl_pattern.finditer(content)]
    # extract templates by <>
    tmpl_str_idx_ranges = []
    for i in range(len(tmpl_steds)):
        cur_start = tmpl_steds[i][1]
        # cur_end = tmpl_steds[i+1][0] if i < len(tmpl_steds)-1 else len(content)
        cur_end = len(content)
        cur_bracket_balance = 1   # how many <s over >s
        for c in range(cur_start, cur_end):
            if content[c] == "<":
                cur_bracket_balance += 1
            elif content[c] == ">":
                cur_bracket_balance -= 1
                if cur_bracket_balance == 0:
                    break
        assert cur_bracket_balance == 0, print(cur_bracket_balance, cur_start, cur_end, content[cur_start:cur_end])
        tmpl_start = tmpl_steds[i][0]
        tmpl_end = c + 1
        tmpl_str_idx_ranges.append((tmpl_start, tmpl_end))
    tmpl_contents = [content[tmpl_str_idx_ranges[i][0]:tmpl_str_idx_ranges[i][1]] for i in range(len(tmpl_str_idx_ranges))]
    ret_codetexts = []
    for i in range(len(tmpl_str_idx_ranges)):
        cur_raw_text = tmpl_contents[i]
        start_line_offset = content[:tmpl_str_idx_ranges[i][0]].count("\n") + 1
        end_line_offset = start_line_offset + cur_raw_text.count("\n") + 1
        ret_codetexts.append(CodeText(
            type = "template",
            name = None,
            text = cur_raw_text.strip(),
            filePath    = filePath,
            startLine   = start_line_offset,
            endLine     = end_line_offset,
            strIdxRange = tmpl_str_idx_ranges[i],
            optionDict  = {}
        ))
    return ret_codetexts


def extract_classes(content, filePath=None):
    # content: C/C++ code string without comments
    class_pattern = re.compile(r'class\s+[^;{]+\s*{', re.MULTILINE)
    class_steds = [(match.start(), match.end()) for match in class_pattern.finditer(content)]
    # extract classes by {}
    class_str_idx_ranges = []
    for i in range(len(class_steds)):
        cur_start = class_steds[i][1]
        cur_end = len(content)
        cur_bracket_balance = 1   # how many {s over }s
        for c in range(cur_start, cur_end):
            if content[c] == "{":
                cur_bracket_balance += 1
            elif content[c] =="}":
                cur_bracket_balance -= 1
                if cur_bracket_balance == 0:
                    break
        assert cur_bracket_balance == 0, print(cur_bracket_balance, cur_start, cur_end, content[cur_start:cur_end])
        class_start = class_steds[i][0]
        class_end = c + content[c:].find(";") + 1
        class_str_idx_ranges.append((class_start, class_end))
    class_contents = [content[class_str_idx_ranges[i][0]:class_str_idx_ranges[i][1]] for i in range(len(class_str_idx_ranges))]
    # format outputs
    ret_codetexts = []
    for i in range(len(class_str_idx_ranges)):
        cur_raw_text = class_contents[i]
        cur_text = cur_raw_text.strip()
        cur_name = cur_text[len("class"):min(cur_text.find("{"),cur_text.find(":"))].strip()
        start_line_offset = content[:class_str_idx_ranges[i][0]].count("\n") + 1
        end_line_offset = start_line_offset + cur_raw_text.count("\n") + 1
        cur_inheritance = None
        if ":" in cur_text[len("class"):cur_text.find("{")]:
            cur_inheritance = cur_text[cur_text.find(":"):cur_text.find("{")].replace(":", " ")
            for cpp_keyword in CPP_KEYWORDS:
                cur_inheritance = cur_inheritance.replace(" "+cpp_keyword+" ", "")
            cur_inheritance = cur_inheritance.strip()
        ret_codetexts.append(CodeText(
            type = "class",
            name = cur_name,
            text = cur_text,
            filePath    = filePath,
            startLine   = start_line_offset,
            endLine     = end_line_offset,
            strIdxRange = class_str_idx_ranges[i],
            optionDict  = {"class_inheritance": cur_inheritance}
        ))
    return ret_codetexts


def extract_definitional_structs(content, filePath=None):
    # content: C/C++ code string without comments
    define_pattern = re.compile(r'struct\s+[^\{\};]+;', re.MULTILINE)
    ret_codetexts = []
    for match in define_pattern.finditer(content):
        start_line_offset = content[:match.start()].count("\n") + 1
        splitted_statements = content[(match.start()+len("struct")):match.end()].replace(";", "").split(" ")
        nontrivial_statements = [s.strip() for s in splitted_statements if s.strip() != ""]
        define_name = nontrivial_statements[0]
        ret_codetexts.append(CodeText(
            type = "struct",
            name = define_name,
            text = content[match.start():match.end()].strip(),
            filePath    = filePath,
            startLine   = start_line_offset,
            endLine     = start_line_offset + 1,
            strIdxRange = (match.start(), match.end()),
            optionDict  = {"struct_type": "definitional"}
        ))
    return ret_codetexts

def extract_multiline_structs(content, filePath=None):
    # content: C/C++ code string without comments
    struct_pattern = re.compile(r'struct\s+[^;{]+\s*{', re.MULTILINE)
    struct_steds = [(match.start(), match.end()) for match in struct_pattern.finditer(content)]
    # extract structs by {}
    struct_str_idx_ranges = []
    for i in range(len(struct_steds)):
        cur_start = struct_steds[i][1]
        cur_end = len(content)
        cur_bracket_balance = 1   # how many {s over }s
        for c in range(cur_start, cur_end):
            if content[c] == "{":
                cur_bracket_balance += 1
            elif content[c] =="}":
                cur_bracket_balance -= 1
                if cur_bracket_balance == 0:
                    break
        assert cur_bracket_balance == 0, print(cur_bracket_balance, cur_start, cur_end, content[cur_start:cur_end])
        struct_start = struct_steds[i][0]
        struct_end = c + content[c:].find(";") + 1
        struct_str_idx_ranges.append((struct_start, struct_end))
    struct_contents = [content[struct_str_idx_ranges[i][0]:struct_str_idx_ranges[i][1]] for i in range(len(struct_str_idx_ranges))]
    # format outputs
    ret_codetexts = []
    for i in range(len(struct_str_idx_ranges)):
        cur_raw_text = struct_contents[i]
        cur_text = cur_raw_text.strip()
        cur_name = cur_text[len("struct"):min(cur_text.find("{"),cur_text.find(":"))].strip()
        start_line_offset = content[:struct_str_idx_ranges[i][0]].count("\n") + 1
        end_line_offset = start_line_offset + cur_raw_text.count("\n") + 1
        cur_inheritance = None
        if ":" in cur_text[len("struct"):cur_text.find("{")]:
            cur_inheritance = cur_text[cur_text.find(":"):cur_text.find("{")].replace(":", " ")
            for cpp_keyword in CPP_KEYWORDS:
                cur_inheritance = cur_inheritance.replace(" "+cpp_keyword+" ", "")
            cur_inheritance = cur_inheritance.strip()
        ret_codetexts.append(CodeText(
            type = "struct",
            name = cur_name,
            text = cur_text,
            filePath    = filePath,
            startLine   = start_line_offset,
            endLine     = end_line_offset,
            strIdxRange = struct_str_idx_ranges[i],
            optionDict  = {"struct_type": "multi-line-struct", "struct_inheritance": cur_inheritance}
        ))
    return ret_codetexts

def extract_structs(content, filePath=None):
    # content: C/C++ code string without comments
    ret_structs = []
    ret_structs.extend(extract_multiline_structs(content=content, filePath=filePath))
    ret_structs.extend(extract_definitional_structs(content=content, filePath=filePath))
    return ret_structs

def extract_functions(content, filePath=None):
    # content: C/C++ code string without comments
    # extract functions with proper input, omit those without any input
    func_pattern = re.compile(r'(\w+)\s*(\w+)\s*\([^\{\}\(\)\=\+\-]+\)\s*{', re.MULTILINE)
    funchead_steds = [(match.start(), match.end()) for match in func_pattern.finditer(content)]
    func_str_idx_ranges = []
    # extract funcs by {}
    for i in range(len(funchead_steds)):
        cur_start = funchead_steds[i][1]
        cur_end = len(content)
        cur_bracket_balance = 1   # how many <s over >s
        for c in range(cur_start, cur_end):
            if content[c] == "{":
                cur_bracket_balance += 1
            elif content[c] =="}":
                cur_bracket_balance -= 1
                if cur_bracket_balance == 0:
                    break
        assert cur_bracket_balance == 0, print(cur_bracket_balance, cur_start, cur_end, content[cur_start:cur_end])
        func_start = funchead_steds[i][0]
        func_end = c + 1
        func_str_idx_ranges.append((func_start, func_end))
    func_contents = [content[func_str_idx_ranges[i][0]:func_str_idx_ranges[i][1]] for i in range(len(func_str_idx_ranges))]
    # format outputs
    ret_codetexts = []
    for i in range(len(func_str_idx_ranges)):
        cur_raw_text = func_contents[i]
        cur_text = cur_raw_text.strip()
        cur_name = [n.strip() for n in cur_text[:cur_text.find("(")].split(" ") if n.strip() != ""][-1]
        if cur_name in CPP_KEYWORDS or not all([fc not in cur_name for fc in [' ', '\n', '\t']]):
            continue    # current function name is invalid
        start_line_offset = content[:func_str_idx_ranges[i][0]].count("\n") + 1
        end_line_offset = start_line_offset + cur_raw_text.count("\n") + 1
        ret_codetexts.append(CodeText(
            type = "function",
            name = cur_name,
            text = cur_text,
            filePath    = filePath,
            startLine   = start_line_offset,
            endLine     = end_line_offset,
            strIdxRange = func_str_idx_ranges[i],
            optionDict  = {}
        ))
    return ret_codetexts


def extract_templated_function_calls(content, filePath=None):
    # content: C/C++ code string without comments
    # extract function calls with template values and non-empty input parameters
    call_pattern = re.compile(r'(\w+)\s*<([^\{\}\(\)\+\-;]+)>\s*\([^\{\}\(\)\=\+\-;]+\)\s*;', re.S)
    call_str_idx_ranges = [(match.start(), match.end()) for match in call_pattern.finditer(content)]
    call_contents = [content[call_str_idx_ranges[i][0]:call_str_idx_ranges[i][1]] for i in range(len(call_str_idx_ranges))]
    # format outputs
    ret_codetexts = []
    for i in range(len(call_str_idx_ranges)):
        cur_raw_text = call_contents[i]
        cur_text = cur_raw_text.strip()
        cur_name = [n.strip() for n in cur_text[:cur_text.find("<")].split(" ") if n.strip() != ""][-1]
        if cur_name in CPP_KEYWORDS or not all([fc not in cur_name for fc in [' ', '\n', '\t']]):
            continue    # current function name is invalid
        start_line_offset = content[:call_str_idx_ranges[i][0]].count("\n") + 1
        end_line_offset = start_line_offset + cur_raw_text.count("\n") + 1
        template_text = cur_text[(cur_text.find("<")+1):cur_text.rfind(">")]
        ret_codetexts.append(CodeText(
            type = "templated_function_call",
            name = cur_name,
            text = cur_text,
            filePath    = filePath,
            startLine   = start_line_offset,
            endLine     = end_line_offset,
            strIdxRange = call_str_idx_ranges[i],
            optionDict  = {"tmpl_text": template_text}
        ))
    return ret_codetexts


def parse_text(text, filePath=None):
    text = clear_comments(text)
    comment_cleared_text = str(text)
    text = clear_ifndefs(text)
    ret_codetexts = []
    # process includes
    extracted_includes = extract_includes(content=text, filePath=filePath)
    text = clear_by_all_strIdxRanges(text=text, all_strIdxRanges=[ct.strIdxRange for ct in extracted_includes])
    # replace all the strings
    text = clear_strings(text)
    # process defines
    extracted_defines = extract_defines(content=text, filePath=filePath)
    text = clear_by_all_strIdxRanges(text=text, all_strIdxRanges=[ct.strIdxRange for ct in extracted_defines])
    # process templates (for later merge with classes, structs, or functions)
    extracted_templates = extract_templates(content=text, filePath=filePath)
    text = clear_by_all_strIdxRanges(text=text, all_strIdxRanges=[ct.strIdxRange for ct in extracted_templates])
    # process classes
    extracted_classes = extract_classes(content=text, filePath=filePath)
    text = clear_by_all_strIdxRanges(text=text, all_strIdxRanges=[ct.strIdxRange for ct in extracted_classes])
    # process structs
    extracted_structs = extract_structs(content=text, filePath=filePath)
    text = clear_by_all_strIdxRanges(text=text, all_strIdxRanges=[ct.strIdxRange for ct in extracted_structs])
    # process functions
    extracted_functions = extract_functions(content=text, filePath=filePath)
    # process function calls
    extracted_calls = extract_templated_function_calls(content=text, filePath=filePath)
    # add templates back to classes, structs, and functions if needed
    tmplable_cts = extracted_classes + extracted_structs + extracted_functions
    for i in range(len(tmplable_cts)):
        _ct = tmplable_cts[i]
        _ct_idxStart, _ct_idxEnd = _ct.strIdxRange
        for j in range(len(extracted_templates)):
            _tmpl = extracted_templates[j]
            _tmpl_idxStart, _tmpl_idxEnd = _tmpl.strIdxRange
            if (_tmpl_idxEnd <= _ct_idxStart) and comment_cleared_text[_tmpl_idxEnd:_ct_idxStart].strip() == "":
                _option_dict = _ct.optionDict
                _option_dict["template"] = _tmpl
                _option_dict["original"] = _ct
                tmplable_cts[i] = CodeText(
                    type = _ct.type,
                    name = _ct.name,
                    text = comment_cleared_text[_tmpl_idxStart:_ct_idxEnd].strip(),
                    filePath    = _ct.filePath,
                    startLine   = _tmpl.startLine,
                    endLine     = _ct.endLine,
                    strIdxRange = (_tmpl.strIdxRange[0], _ct.strIdxRange[1]),
                    optionDict  = _option_dict
                )
                break
    # done processing, return extracted codetexts
    ret_codetexts.extend(extracted_includes)
    ret_codetexts.extend(extracted_defines)
    ret_codetexts.extend(extracted_calls)
    ret_codetexts.extend(tmplable_cts)
    return ret_codetexts

def parse_file(filePath):
        with open(filePath, 'r', encoding='utf-8', errors='ignore') as f:  # ignore invalid bytes
            text = f.read()
        return parse_text(text=text, filePath=filePath)