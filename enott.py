import os
import json
import sys
import datetime
import pathlib
from prettytable import PrettyTable


default_backend='zathura'
backend=None


class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'


def start_zathura():
    os.system('zathura view/output.pdf')


def start_viewer(viewer):
    acceptable_viewers = {'zathura': start_zathura}
    if viewer in acceptable_viewers:
        view_executor = acceptable_viewers[viewer]
        view_executor()
    else:
        raise NotImplementedError(f"Unsupported backend")


def get_date_last_modified(file):
    return datetime.datetime.fromtimestamp(pathlib.Path(file).stat().st_mtime)


def any_new_modified(path, extension, compare):
    for file in os.listdir(path):
        if file.endswith(extension) and get_date_last_modified(file) >= compare:
            return True

    return False



def get_old_tags(note_name):
    path = f"{note_name}/meta.json"
    if not os.path.exists(path):
        raise FileNotFoundError(f"Could not locate '{note_name}/meta.json'")
    with open(path, 'r') as f:
        data = json.load(f)
        if not "tags" in data:
           raise ValueError("Missing tags in meta.json")
        return data["tags"]

    return []


def view_current(name):
    if not name:
        return False

    if not os.path.exists(name):
        raise FileNotFoundError(f"Cannot find note {name}")

    os.chdir(name)
    return True


def compile_current(name):
    print("Compiling...")
    os.system(f"pdflatex -jobname=output -output-directory=view {name}.tex")
    os.system("touch meta.json")


def view_note(name=None):
    global backend
    global default_backend

    if name != None and name.endswith('/'):
        view_note(name[:-1])

    step_back = view_current(name)
    if not os.path.isdir('view'):
        raise FileNotFoundError("Missing directory 'view'")
    
    meta_last_modified = get_date_last_modified('meta.json')
    if any_new_modified(path='./', extension='.tex', compare=meta_last_modified):
        compile_current(name)

    selected_backend = backend
    if backend == None:
        print("Using default backend...")
        selected_backend = default_backend
    start_viewer(selected_backend)

    if step_back:
        os.chdir('../')


def remove_tag(name, tags):
    if not os.path.exists(name):
        raise FileNotFoundError(f"Could not locate '{name}'")
    path = f"{name}/meta.json"
    old_tags = get_old_tags(name)
    with open(path, 'w') as f:
        f.write(f"{{\n\"tags\": {json.dumps(list(set(old_tags) - set(tags)))}\n}}")


def mode_remove_tag():
    if len(sys.argv) < 4:
        raise ValueError("Mismatch in expected arguments for the use of the remove-tag mode. Use 'enott help' for usage.")
    remove_tag(sys.argv[2], parse_tags(sys.argv[3]))


def mode_remove():
    if len(sys.argv) < 3:
        raise ValueError("Mismatch in expected arguments for the use of the remove-note mode. Use 'enott help' for usage.")
    remove_note(sys.argv[2])


def remove_note(name):
    if not os.path.exists(name):
        raise FileNotFoundError(f"Could not locate '{name}'")
    path = f"{name}/meta.json"
    if not os.path.exists(path):
        raise FileNotFoundError(f"Could not locate '{name}/meta.json', you are probably making a mistake deleting this...")
    answer = input(f"Are you sure you want to remove {name}? This action cannot be undone.: ")
    if answer.lower().startswith('y'):
        os.system(f"rm -rf {name}")
    print(f"Succesfully removed note {name}")


def display_help():
    table = PrettyTable()
    table.field_names = [f"{color.BOLD} Help {color.END}"]
    table.add_rows([
        ["enott add <note-name> -template=<template-name> -tags=<tag1>,<tag2>,..."],
        ["enott add-tag <note-name> <tag1>,<tag2>,..."],
        ["enott remove <note-name>"],
        ["enott remove-tag <note-name> <tag1>,<tag2>,..."],
        ["enott search -filter=<tag1>,<tag2>,..."],
        ["enott view <note-name>"],
    ])
    print(table)


def add_tag(name, tags):
    if not os.path.exists(name):
        raise FileNotFoundError(f"Could not locate {name}")
    path = f"{name}/meta.json"
    old_tags = get_old_tags(name)
    with open(path, 'w') as f:
        f.write(f"{{\n\"tags\": {json.dumps(list(set(old_tags).union(tags)))}\n}}")


def matches_tags(note_name, filter_tags):
    path = note_name + "/meta.json"
    if not os.path.exists(path):
        return None
    note_tags = set(get_old_tags(note_name))
    if set(filter_tags) <= set(note_tags):
        return (note_name, note_tags)

    return None


def search(filter_tags=[]):
    for note in os.listdir("./"):
        result = matches_tags(note, filter_tags)
        if result:
            yield result


def add_note(name, template='default', tags=[]):
    if '/' in name:
        raise ValueError('A name cannot contain a \'/\' character')
    if os.path.exists(name):
        raise FileExistsError("Cannot create a note when the note name is already taken in the path")
    if not template.endswith('.tex'):
        template += '.tex'
    if not os.path.exists(template):
        raise FileNotFoundError(f"Cannot find template file '{template}'.")
    path = name + "/"
    print(f"Using template {template}...")
    print("Creating path...")
    os.makedirs(path)
    print("Creating assets path...")
    os.makedirs(path + "/assets")
    print("Creating view path...")
    os.makedirs(path + "/view")

    with open(path + name + ".tex", 'w') as dest, open(template, 'r') as src:
        print("Copying template...")
        for line in src:
            dest.write(line)
    print("Adding tags...")
    with open(path + "/meta.json", 'w') as dest:
        dest.write('{\n')
        dest.write(f"\"tags\": {json.dumps(tags)}")
        dest.write('\n}')
    os.chdir(name)
    compile_current(name)
    os.chdir('../')
    print("=== Done! ===")


def parse_tags(s):
    return s.split(",")


def mode_add():
    name = sys.argv[2]
    template = 'default'
    tags = []

    for arg in sys.argv[3:]:
        if arg.startswith("-template="):
            template = arg[len("-template="):]
        elif arg.startswith("-tags="):
            tags = parse_tags(arg[len("-tags="):])
        else:
            raise ValueError(f"Invalid argument {arg}")

    add_note(name, template, tags)


def mode_add_tag():
    if len(sys.argv) < 4:
        raise ValueError("Misuse of \'add-tag\' mode, use 'enott help' to see the format of this mode")
    add_tag(sys.argv[2], parse_tags(sys.argv[3]))


def prettify_search_tag(tag, filter_tags):
    return color.GREEN + color.BOLD + tag + color.END if tag in filter_tags else tag


def create_pretty_table(tags):
    table_contents = list(map(lambda x: [x[0],  ','.join(map(lambda y: prettify_search_tag(y, tags), x[1]))], search(tags)))
    if len(table_contents) == 0:
        return None
    table = PrettyTable()
    table.field_names = [f"{color.BOLD} Name {color.END}", f"{color.BOLD} Tags {color.END}"]
    table.align[table.field_names[0]] = 'l';
    table.align[table.field_names[1]] = 'l';
    for row in table_contents:
        table.add_row(row)

    return table


def mode_search():
    tags = []

    for arg in sys.argv[2:]:
        if arg.startswith("-filter="):
            tags = parse_tags(arg[len("-filter="):])
        else:
            raise ValueError(f"Invalid argument \'{arg}\'")
      
    table = create_pretty_table(tags)
    no_table_message = "No matches found for given tags."
    print(table if table else no_table_message)


def mode_view():
    name = None
    if len(sys.argv) >= 3:
        name = sys.argv[2]
    view_note(name)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("Missing mode, type 'enott help' for usage")

    mode_options = {
        "add": mode_add,
        "search": mode_search,
        "help": display_help,
        "add-tag": mode_add_tag,
        "view": mode_view,
        "remove-tag": mode_remove_tag,
        "remove": mode_remove,
    }
    
    try:
        mode = sys.argv[1]

        if not mode in mode_options:
            raise ValueError(f"Invalid mode \'{mode}\'")
        mode_options[mode]()
    except Exception as e:
        print(f"Error: {e}")
