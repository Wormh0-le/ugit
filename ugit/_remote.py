import os

from . import data
from . import base

REMOTE_REFS_BASE = 'refs/heads/'
LOCAL_REFS_BASE = 'refs/remote/'

def fetch(remote_path):
    # print("Will fetch the following refs:")
    # for refname, _ in _get_remote_refs(remote_path, 'refs/heads'):
    #     print(f'- {refname}')
    # Get refs from server
    refs = _get_remote_refs(remote_path, REMOTE_REFS_BASE)
    # Fetch missing objects by iterating and fetching on demand
    for oid in base.iter_objects_in_commits(refs.values()):
        data.fetch_object_if_missing(oid, remote_path)

    # Update local refs to match server
    for remote_name, value in refs.items():
        refname = os.path.relpath(remote_name, REMOTE_REFS_BASE)
        data.update_ref(f"{LOCAL_REFS_BASE}/{refname}", data.RefValue(symbolic=False, value=value))

def _get_remote_refs(remote_path, prefix = ''):
    with data.change_git_dir(remote_path):
        return {refname : ref.value for refname, ref in data.iter_refs(prefix)}

def push(remote_path, refname):
    remote_refs = _get_remote_refs(remote_path)
    remote_ref = remote_refs.get(refname)
    local_ref = data.get_ref(refname).value
    assert local_ref

    assert not remote_ref or base.is_ancestor_of(local_ref, remote_ref)

    # Compute which objects the server doesn't have
    known_remote_refs = filter(data.object_exists, remote_refs.values())
    remote_objects = set(base.iter_objects_in_commits(known_remote_refs))
    local_objects = set(base.iter_objects_in_commits({local_ref}))
    objects_to_push = local_objects - remote_objects

    # objects_to_push = base.iter_objects_in_commits({local_ref})
    for oid in objects_to_push:
        data.push_object(oid, remote_path)
    
    with data.change_git_dir(remote_path):
        data.update_ref(refname, data.RefValue(symbolic=False, value=local_ref))