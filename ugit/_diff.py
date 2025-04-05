import difflib
import merge3
from collections import defaultdict

from . import data


def compare_trees(*trees):
    entries = defaultdict(lambda: [None] * len(trees))
    for i, tree in enumerate(trees):
        for path, oid in tree.items():
            entries[path][i] = oid
    
    for path, oids in entries.items():
        yield (path, *oids)
    
def iter_changed_files(t_from, t_to):
    for path, o_from, o_to in compare_trees(t_from, t_to):
        if o_from != o_to:
            action = (
                'new file' if not o_from else
                'delted' if not o_to else
                'modified'
            )
            yield path, action

def diff_trees(t_from, t_to):
    output = ''
    for path, o_from, o_to in compare_trees(t_from, t_to):
        if o_from != o_to:
            # output += f"changed: {path}\n"
            output += diff_blobs(o_from, o_to, path)
    
    return output

def merge_trees(t_base, t_HEAD, t_other):
    tree = {}
    for path, o_base, o_HEAD, o_other in compare_trees(t_base, t_HEAD, t_other):
        tree[path] = data.hash_object(merge_blobs(o_base, o_HEAD, o_other))
    return tree

def merge_blobs(o_base, o_HEAD, o_other):
    content_base = data.get_object(o_base) if o_base else b''
    content_HEAD = data.get_object(o_HEAD) if o_HEAD else b''
    content_other = data.get_object(o_other) if o_other else b''

    base_lines = content_base.decode(errors='replace').splitlines(keepends=True)
    HEAD_lines = content_HEAD.decode(errors='replace').splitlines(keepends=True)
    other_lines = content_other.decode(errors='replace').splitlines(keepends=True)
    merger = merge3.Merge3(base_lines, other_lines, HEAD_lines)
    merged_lines = merger.merge_lines()
    return ''.join(merged_lines)

# def merge_blobs(o_HEAD, o_other):
#     content_HEAD = data.get_object(o_HEAD) if o_HEAD else b''
#     content_other = data.get_object(o_other) if o_other else b''

#     merged = []
#     matcher = difflib.SequenceMatcher(
#         None, content_HEAD.decode(errors='replace').splitlines(), 
#         content_other.decode(errors='replace').splitlines()
#     )
#     for opcode, a_start, a_end, b_start, b_end in matcher.get_opcodes():
#         if opcode == 'equal':
#             merged.append(content_HEAD[a_start:a_end])
#         else:
#             merged.append(f"<<<<<< HEAD{o_HEAD}\n{content_HEAD[a_start:a_end]}")
#             merged.append("======")
#             merged.append(f">>>>>> others{o_other}\n{content_other[b_start:b_end]}")
#     return '\n'.join(merged)

def diff_blobs(o_from, o_to, path='blob'):
    content_from = data.get_object(o_from) if o_from else b''
    content_to = data.get_object(o_to) if o_to else b''
    diff = difflib.unified_diff(content_from.decode(errors='replace').splitlines(), content_to.decode(errors='replace').splitlines(), f'a/{path}', f'b/{path}')
    return '\n'.join(diff)
    
