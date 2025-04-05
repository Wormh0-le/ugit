import os
import sys
import typer
import textwrap
import subprocess

from typing_extensions import Annotated
from typing import List, Optional

from . import base
from . import data
from . import _diff
from . import _remote

app = typer.Typer()

@app.command()
def init():
    base.init()
    typer.echo(f"Initialized empty ugit repository in {os.getcwd()}/{data.GIT_DIR}")

@app.command()
def hash_object(file: str):
    with open(file, "rb") as f:
        typer.echo(data.hash_object(f.read()))

@app.command()
def cat_file(object: Annotated[str, typer.Argument(callback=base.get_oid)]):
    sys.stdout.flush()
    sys.stdout.buffer.write(data.get_object(object, expected=None))


@app.command()
def write_tree():
    print(base.write_tree())

@app.command()
def read_tree(tree: Annotated[str, typer.Argument(callback=base.get_oid)]):
    base.read_tree(tree)

@app.command()
def commit(message: Annotated[str, typer.Option("--message", "-m")]):
    typer.echo(base.commit(message))

def _print_commit(oid, commit, refs=None):
    ref_str = f" ({','.join(refs)})" if refs else ""
    print(f"commit {oid} {ref_str}\n")
    print(textwrap.indent(commit.message, '    '))
    print("")

@app.command()
def log(oid: Annotated[str, typer.Option(callback=base.get_oid)]='@'):
    refs = {}
    for refname, ref in data.iter_refs():
        refs.setdefault(ref.value, []).append(refname)

    for oid in base.iter_commits_and_parents({oid}):
        commit = base.get_commit(oid)
        _print_commit(oid, commit, refs.get(oid))

@app.command()
def show(oid: Annotated[str, typer.Option(callback=base.get_oid)]='@'):
    if not oid:
        return
    commit = base.get_commit(oid)
    parent_tree = None
    if commit.parents:
        parent_tree = base.get_commit(commit.parents[0]).tree
    _print_commit(oid, commit)
    result = _diff.diff_trees(base.get_tree(parent_tree), base.get_tree(commit.tree))
    sys.stdout.flush()
    sys.stdout.write(result)

@app.command()
def diff(commit: Annotated[Optional[str], typer.Argument()]=None, cached: Annotated[bool, typer.Option('--cached')]=False):
    oid = commit and base.get_oid(commit)
    if commit:
        tree_from = base.get_tree(oid and base.get_commit(oid).tree)
    
    if cached:
        tree_to = base.get_index_tree()
        if not commit:
            oid = base.get_oid('@')
            tree_from = base.get_tree(oid and base.get_commit(oid).tree)
    else:
        tree_to = base.get_working_tree()
        if not commit:
            tree_from = base.get_index_tree()
    
    result = _diff.diff_trees(tree_from, tree_to)
    sys.stdout.flush()
    sys.stdout.write(result)

# @app.command()
# def checkout(oid: Annotated[str, typer.Argument(callback=base.get_oid)]):
#     base.checkout(oid)

@app.command()
def checkout(commit: Annotated[str, typer.Argument()]):
    base.checkout(commit)

@app.command()
def tag(name: Annotated[str, typer.Option()], oid: Annotated[str, typer.Option(callback=base.get_oid)]='@'):
    base.create_tag(name, oid)

@app.command()
def branch(name: Annotated[str, typer.Argument()]='', start_point: Annotated[str, typer.Option(callback=base.get_oid)]='@'):
    if not name:
        current = base.get_branch_name()
        for branch in base.iter_branch_names():
            prefix = '*' if branch == current else ' '
            print(f"{prefix} {branch}")
    else:
        base.create_branch(name, start_point)
        print(f"Branch {name} created at {start_point[:10]}")

@app.command()
def k():
    dot = 'digraph commits {\n'
    oids = set()
    for refname, ref in data.iter_refs(deref=False):
        # print(refname, ref)
        dot += f"'{refname}' [shape=note]\n"
        dot += f"'{refname}' -> '{ref.value}'\n"
        if not ref.symbolic: 
            oids.add(ref.value)
    
    for oid in base.iter_commits_and_parents(oids):
        commit = base.get_commit(oid)
        # print(oid)
        # dot.node(oid, shape='box', label=oid[:10], style='filled')
        dot += f"'{oid}' [shape=box, style=filled label='{oid[:10]}']\n"
        # if commit.parent:
            # print('Parent', commit.parent)
            # dot.edge(oid, commit.parent)
            # dot += f"'{oid}' -> '{commit.parent}'\n"
        for parent in commit.parents:
            dot += f"'{oid}' -> '{parent}'\n"
    dot += '}'
    print(dot)
    with subprocess.Popen(['dot', '-Tgtk', '/dev/stdin'], stdin=subprocess.PIPE) as proc:
        proc.communicate(dot.encode())

@app.command()
def status():
    HEAD = base.get_oid("@")
    branch = base.get_branch_name()
    if branch:
        print(f"On branch {branch}")
    else:
        print(f"HEAD detached at {HEAD[:10]}")
    MERGED_HEAD = data.get_ref('MERGED_HEAD').value
    if MERGED_HEAD:
        print(f"Merging branch {MERGED_HEAD[:10]}")
    print("\nChanges to be commited:\n")
    HEAD_tree = HEAD and base.get_commit(HEAD).tree
    for path, action in _diff.iter_changed_files(base.get_tree(HEAD_tree), base.get_index_tree()):
        print(f"{action:>12}: {path}")
    print("\nChanges not staged for commit:\n")
    for path, action in _diff.iter_changed_files(base.get_index_tree(), base.get_working_tree()):
        print(f"{action:>12}: {path}")


@app.command()
def reset(commit: Annotated[str, typer.Option(callback=base.get_oid)]):
    base.reset(commit)

@app.command()
def merge(commit: Annotated[str, typer.Argument(callback=base.get_oid)]):
    base.merge(commit)

@app.command()
def merge_base(commit1: Annotated[str, typer.Argument(callback=base.get_oid)], commit2: Annotated[str, typer.Argument(callback=base.get_oid)]):
    print(base.get_merge_base(commit1, commit2))

@app.command()
def fetch(remote: Annotated[str, typer.Argument()]):
    _remote.fetch(remote)

@app.command()
def push(remote: Annotated[str, typer.Argument()], branch: Annotated[str, typer.Argument()]):
    _remote.push(remote, f"refs/heads/{branch}")

@app.command()
def add(files: Annotated[List[str], typer.Argument()]):
    base.add(files)

def main():
    with data.change_git_dir('.'):
        app()


if __name__ == "__main__":
    main()