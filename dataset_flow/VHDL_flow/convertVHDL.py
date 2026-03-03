import os

sh_filename = 'script2.sh'
repoPath = ''

def add_line_to_sh_file(filename, line):
    with open(filename, 'a') as file:
        file.write(line + '\n')

# Add lines to the .sh file
add_line_to_sh_file(sh_filename, '#!/bin/bash')
add_line_to_sh_file(sh_filename, 'total_count=0')

for root, dirs, files in os.walk(repoPath):
    for file in files:
        file_path = os.path.join(root, file)
        filename = os.path.basename(file_path)
        if file_path.endswith('.vhd'):
            outputFile = filename[:len(filename[:len(filename)-4])] + ".v"
            add_line_to_sh_file(sh_filename,'count=$(find . -type f -name "*.v" | wc -l)')
            add_line_to_sh_file(sh_filename, f'cd "{os.path.dirname(file_path)}"')
            add_line_to_sh_file(sh_filename, f'vhd2vl "{filename}" "{outputFile}" &> {outputFile[:len(outputFile)-2]}_error.txt')
            add_line_to_sh_file(sh_filename,'count2=$(find . -type f -name "*.v" | wc -l)')
            add_line_to_sh_file(sh_filename, 'total_count=$((total_count+count2-count1))')

add_line_to_sh_file(sh_filename, 'echo "Final Total: $total_count"')