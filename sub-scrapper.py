#! /usr/bin/python
# -*- coding: utf-8 -*-
'''
    ante problemas:
    sudo apt-get remove python-pip
    sudo easy_install pip

    pip install patool
    pip install robobrowser
    pip install flask
    pip install lxml
'''
import os
import zipfile
import patoolib
import sys
import re
import requests
from robobrowser import RoboBrowser
import json


# ######################################### CONSTANTS #########################################

VERSION = "0.4"
DEFAULT_PARSER = "lxml"
TEMPLATE_URL = "http://www.subdivx.com/index.php?q={}&accion=5&masdesc=&subtitulos=1&realiza_b=1"
EMPTY_SPACE = "%20"
NO_RESULT_STR = "No encontramos resultados con el buscador de subdivx. Probemos con el de Google"

PARAMS_DEFAULT_CONFIG = {
        "QUERY_TEXT" : None,
        "REFINE_REGEX" : ".*",
        "RESULT_LIMIT": 1,
        "SEND_TO_MEDIA_SERVER" : False,
        "SEND_TO_MEDIA_SERVER_PATH": "dagobah@192.168.0.104:/media/removable/Seagat*/MEDIA_DOWNLOAD",
        "MODE":"SCRIPT", # SCRIPT | SERVER
        "SHOW_POST_JSON_QUERY_EXAMPLE" : False
    }

PARAMS_BY_PREFIX = {
            "q":"QUERY_TEXT",
            "r":"REFINE_REGEX",
            "l":"RESULT_LIMIT",
            "s":"SEND_TO_MEDIA_SERVER",
            "u":"SEND_TO_MEDIA_SERVER_PATH",
            "m":"MODE",
            "e":"SHOW_POST_JSON_QUERY_EXAMPLE"
        }

PARAMS_TYPE  = {
            "QUERY_TEXT":"str",
            "REFINE_REGEX":"str",
            "RESULT_LIMIT":"int",
            "SEND_TO_MEDIA_SERVER":"bool",
            "SEND_TO_MEDIA_SERVER_PATH":"str",
            "MODE":"str",
            "SHOW_POST_JSON_QUERY_EXAMPLE":"bool"
        }

VIDEO_FILE_EXTENSIONS = ('264', 'avi', 'flv', 'h264', 'hdmov', 'mkv', 'mp4', 'mp4v', 'mpeg', 'mpeg1', 'mpeg4', 'ogm',
'rm', 'xmv', 'xvid', 'zmv' )

SUB_FILE_EXTENIONS = ('srt', 'sub')

# ######################################### "PRIVATE" METHODS #########################################

def __get_url__(query_text):
    query_text_scaped = query_text.replace(" ", EMPTY_SPACE)
    return TEMPLATE_URL.format(query_text_scaped)

def __equals_ignore_case__(a, b):
    return a.upper() == b.upper()

def __string_array_to_lower__(str_array):
	return map(lambda s: s.lower(), str_array)

def __match_exp__(regex, text):
    return re.match(regex, text, re.IGNORECASE) != None

def __download_sub__(url):

    file_id = url.split("?")[1].split("&")[0].split("=")[1]

    # get request
    file_name = None
    response = requests.get(url)
    content_type = response.headers["Content-Type"]
    if (content_type == "application/x-rar-compressed"):
        file_name = file_id + ".rar"
    elif (content_type == "application/zip"):
        file_name = file_id + ".zip"
    else:
        raise Exception("Unkown content type: " + content_type)

    # open in binary mode
    with open(file_name, "wb") as file:
        # write to file
        file.write(response.content)

def __parse_param_value__(param_name, param_value):
    if PARAMS_TYPE[param_name] == "str":
        return param_value

    if PARAMS_TYPE[param_name] == "int":
        return int(param_value)

    if PARAMS_TYPE[param_name] == "bool":
        return param_value == "true"

def __get_config__(args):
    '''
        INPUT: key - value params
    '''
    config = PARAMS_DEFAULT_CONFIG.copy()
    if len(args) == 0:
        return config

    cur_param_name = None
    for arg in args:

        if arg == None:
            continue

        cur_arg = arg.strip().lower()

        if cur_arg == "":
            continue

        if (cur_param_name == None):
            # then cur_arg must be a prefix
            cur_param_name = PARAMS_BY_PREFIX.get(cur_arg.replace("-",""))
            if (cur_param_name == None):
                log_and_exit("No param found with name: {}".format(cur_arg))
        else:
            cur_arg_parsed = __parse_param_value__(cur_param_name, cur_arg)
            config[cur_param_name] = cur_arg_parsed
            cur_param_name = None

    return config

def log(text):
    print("> " + str(text))

def log_and_exit(text):
    log(text)
    sys.exit(0)

def __get_example_server_call__():
    example_config = PARAMS_DEFAULT_CONFIG.copy()
    example_config["QUERY_TEXT"] = "homeland s01e01"
    return example_config

def __show_example_server_call__():
    log("Example call: \nPOST: localhost:5000/subtitles")
    example_config = PARAMS_DEFAULT_CONFIG.copy()
    example_config["QUERY_TEXT"] = "homeland s01e01"
    print (json.dumps(example_config, indent=4))
    print ("------------------------------------")


def __split_file_name__(full_file_name):
    '''
        Returns a tuple: (name, extension)
    '''

    if full_file_name == None:
        return (None, None)

    full_file_name = full_file_name.strip().lower()

    if "." in full_file_name:
        file_extension = full_file_name.split(".")[-1]
        file_name = full_file_name.replace("." + file_extension, "").lower()
        return (file_name, file_extension)
    else:
        return (full_file_name, None)


def __transform_name__(str):
    regex_template = "^.*S[0-9]{2}E[0-9]{2}|^.*s[0-9]{2}e[0-9]{2}"
    regex_result = re.match(regex_template, str, re.IGNORECASE)
    if regex_result == None:
        return str
    else:
        return regex_result.group(0)

def __search_by_scanning__(config):
    '''
        Scans foder, and retrieve the subtitles for video files without them
    '''

    video_file_names = []
    sub_file_names = []
    result_divs = []

    for cur_file in os.listdir("."):
        splitted_file_name = __split_file_name__(cur_file)
        cur_file_name = splitted_file_name[0]
        cur_file_ext = splitted_file_name[1]

        if cur_file_ext in VIDEO_FILE_EXTENSIONS:
            video_file_names.append(cur_file_name)

        if cur_file_ext in SUB_FILE_EXTENIONS:
            sub_file_names.append(cur_file_name)

    videos_without_subs = filter(lambda v: v not in sub_file_names, video_file_names)
    log("videos_without_subs: " + videos_without_subs.__str__())

    for video_without_subs in videos_without_subs:
        print "---" * 5
        print "Original query text: " + video_without_subs
        resolved_query_text = __transform_name__(video_without_subs)
        print "Resolved query text: " + resolved_query_text
        config["QUERY_TEXT"] = resolved_query_text
        current_result_divs = __search_by_config__(config)
        if current_result_divs != None:
            result_divs.extend(current_result_divs)

    return result_divs


def __search_by_config__(config):
    '''
        Returns an array of elements with: name, detail, url
    '''
    # ----- start browser -----
    browser = RoboBrowser(history=True)
    browser.parser = "lxml"

    query_url = __get_url__(config["QUERY_TEXT"])
    log ("Query Url: \t\t" + query_url)
    browser.open(query_url)

    all_content = browser.find_all().__str__()
    has_init_results =  NO_RESULT_STR in all_content
    log ("Has initial results: \t" + has_init_results.__str__())

    # ----- create raw results list -----
    all_divs = browser.select("div")
    results = []
    current_result = {}
    for div in all_divs:
        div_id = div.get("id")

        if (div_id == "menu_detalle_buscador"):
            current_result = {}
            current_result["name"] = div.select("#menu_titulo_buscador a")[0].text
            # print  dir(div)

        if (div_id == "buscador_detalle"):
            current_result["detail"] = div.select("#buscador_detalle_sub")[0].text
            current_links = div.select("#buscador_detalle_sub_datos a")
            for current_link in current_links:
                current_link_href = current_link.get("href").__str__()
                if "bajar.php" in current_link_href:
                    current_result["url"] = current_link_href
            results.append(current_result)

    # ----- apply regex -----
    result_divs = filter(lambda item: __match_exp__(config["REFINE_REGEX"], item["detail"]) , results)

    # ----- apply limit -----
    result_divs = result_divs[:config["RESULT_LIMIT"]]

    return result_divs


# ######################################### OTHER STEPS #########################################
def __post_retrieve__(config, result_divs):
    # ----- download subtitles -----
    log("Downloadind links ...")
    for r in result_divs:
        sub_name_for_log = r["name"] + " " + r["detail"]
        log("\t" + r["url"] + " (" + sub_name_for_log.encode('utf-8')[:80]  + ")")
        __download_sub__(r["url"])

    # ----- handle downloads -----
    log("Extracting content ...")
    for file_name in os.listdir("."):
        if (".rar" in file_name.lower() or ".zip" in file_name.lower()):
            patoolib.extract_archive(file_name, outdir=".", verbosity=-1, interactive=False)
    os.system('rm -f *.rar')
    os.system('rm -f *.zip')

    # ----- move files to server -----
    if (config["SEND_TO_MEDIA_SERVER"]):
        log("Sending to media server ...")
        os.system("scp ./*.srt {}".format(config["SEND_TO_MEDIA_SERVER_PATH"]))

# ######################################### MODE SERVER #########################################

def __start_server__():
    from flask import Flask, request, jsonify

    app = Flask(__name__)

    @app.route("/example", methods=["GET"])
    def get_example():
        config = request.json
        return jsonify(__get_example_server_call__())

    @app.route("/subtitles", methods=["GET"])
    def get_example_2():
        config = request.json
        return jsonify(__get_example_server_call__())

    @app.route("/subtitles", methods=["POST"])
    def find_subtitles():
        config = request.json
        return jsonify(config)

    app.run()


# ######################################### MAIN #########################################

if __name__ == "__main__":
    print ("####################################")
    print ("------------------------------------")
    print (" sub-scrapper " + VERSION)
    print ("------------------------------------")

    # ----- handle arguments -----
    args = sys.argv[1:]
    args = __string_array_to_lower__(args)
    config = __get_config__(args)

    for k,v in config.iteritems():
        log("{} => {}".format(k.lower().replace("_"," "), v))

    print ("------------------------------------")

    # ----- show the default json config
    if (config["SHOW_POST_JSON_QUERY_EXAMPLE"]):
        __show_example_server_call__()
        sys.exit(0)

    result_divs = None
    # ----- MODE SERVER -----
    if (__equals_ignore_case__(config["MODE"], "SERVER")):
        __show_example_server_call__()
        __start_server__()

    # ----- MODE SCANNER -----
    if (__equals_ignore_case__(config["MODE"], "SCANNER")):
        result_divs = __search_by_scanning__(config)
        
    # ----- MODE SCRIPT -----
    if (__equals_ignore_case__(config["MODE"], "SCRIPT")):
        result_divs = __search_by_config__(config)

    # ----- POST RUN HANDLING -----
    __post_retrieve__(config, result_divs)

    log ("Done!")

    print ("------------------------------------")
    print ("####################################")
