# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from termcolor import colored
import re
from copy import copy


def make_text(input, output=False):
    """ Perform transformation to raw text, adding markers

    :param input: name of file to transform
    :param output: name of output file to create
    :type input: string
    :type output: list if True
    :return:
    """
    file_exists = True
    try:
        with open(input, "r") as f:
            text_input = f.read()
        soup = BeautifulSoup(text_input, "lxml-xml")
    except Exception as e:
        file_exists = False
        print(colored("Error:", "red", attrs=["bold"]), e)

    if file_exists:
        all_pages = soup.find_all("page")
        for page in all_pages:
            all_blocks = page.find_all("block")
            for block in all_blocks:
                # modify figure type blocks, including tables
                if block["blockType"] != "Text":
                    block.name = "figure"
                    block["type"] = block["blockType"]
                    attrs_list = block.attrs
                    for attr in list(attrs_list):
                        if attr != "type":
                            del block[attr]
                    block.clear()
                # rearrange text type blocks
                else:
                    if block.region:
                        block.region.decompose()
                    # moving par elements right under block element
                    all_pars = block.find_all("par")
                    for par in all_pars:
                        ext_par = par.extract()
                        ext_par.name = "p"
                        block.append(ext_par)
                    # finding a way around to delete tag names text
                    all_tags = block.contents
                    for tag in all_tags:
                        if tag.name == "text":
                            tag.decompose()
                    # moving line elements right under par element
                    all_lines = block.find_all("line")
                    for line in all_lines:
                        line.append(line.formatting.string)
                        f_attrs_list = line.formatting.attrs
                        if len(f_attrs_list) > 0:
                           for f_attr in f_attrs_list:
                               line[f_attr] = f_attrs_list[f_attr]
                        line.formatting.decompose()
                    block["type"] = "Text"
                    del block["blockName"]
                    block.name = "div"
        # preparing alternative soup with only removed items
        guard = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><document xmlns="http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml" version="1.0" producer="timeUs"></document>"""
        guard_soup = BeautifulSoup(guard, "lxml-xml")
        all_pages = soup.find_all("page")
        warning_headers = []
        warning_signatures = []
        count_page = 0
        for page in all_pages:
            count_page += 1
            page["id"] = "page%s" % count_page
            page_f = copy(page)
            page_f.clear()
            all_divs = page.find_all("div")
            count_div = 0
            for div in all_divs:
                count_div += 1
                div["id"] = "page%s_div%s" % (count_page, count_div)
                div_f = copy(div)
                div_f.clear()
                all_ps = div.find_all("p")
                count_p = 0
                for p in all_ps:
                    count_p += 1
                    p["id"] = "page%s_div%s_p%s" % (count_page, count_div, count_p)
                    p_f = copy(p)
                    p_f.clear()
                    all_lines = p.find_all("line")
                    count_line = 0
                    for line in all_lines:
                        # targetting headers
                        if int(line["b"]) < (int(page["height"]) * 0.12):
                            if "lineSpacing" in line.parent.attrs:
                                if (int(line.parent["lineSpacing"]) <= 750) and (int(line.parent["lineSpacing"]) >= 390):
                                    line_f = line.extract()
                                    line_f["type"] = "header"
                                    p_f.append(line_f)
                                else:
                                    count_line += 1
                                    line["id"] = "page%s_d%s_p%s_l%s" % (count_page, count_div, count_p, count_line)
                                    test_str = line.string
                                    if len(test_str.replace(" ", "")) < 55:
                                        print(colored("WARNING:", "yellow", attrs=["reverse"]), "line might be a header but was left in output: '%s'.\n\t" % (line["id"]), colored(line.string, "white", attrs=["dark"]))
                            else:
                                count_line += 1
                                line["id"] = "page%s_d%s_p%s_l%s" % (count_page, count_div, count_p, count_line)
                                print(colored("WARNING:", "yellow", attrs=["reverse"]), "line might be a header but was left in output: '%s'.\n\t" % (line["id"]), colored(line.string, "white", attrs=["dark"]))
                        # targetting signatures
                        elif int(line["b"]) > (int(page["height"]) * 0.91):
                            if len(line.string) <= 2:
                                line_f = line.extract()
                                line_f["type"] = "signature"
                                p_f.append(line_f)
                            elif len(line.string) >= 3 and len(line.string) < 10:
                                count_line += 1
                                line["id"] = "page%s_d%s_p%s_l%s" % (count_page, count_div, count_p, count_line)
                                print(colored("WARNING:", "yellow", attrs=["reverse"]),
                                      "line might be a signature but was left output: '%s'.\n\t" % (line["id"]),
                                      colored(line.string, "white", attrs=["dark"]))
                            else:
                                count_line += 1
                                line["id"] = "page%s_d%s_p%s_l%s" % (count_page, count_div, count_p, count_line)
                        else:
                            count_line += 1
                            line["id"] = "page%s_d%s_p%s_l%s" % (count_page, count_div, count_p, count_line)
                    if len(p_f.contents) > 0:
                        div_f.append(p_f)
                if len(div_f.contents) > 0:
                    page_f.append(div_f)
            guard_soup.document.append(page_f)

        # ...
        # - recompose paragraphs
        # - identify title
        # - add management of location within the article from titles and headers

        final_str = str(soup.prettify())
        guard_str = str(guard_soup.prettify())

        # Making name for output file
        if not output:
            input = input.split(".")
            output = str(input[0]) + "_out.xml"
            output_guard = str(input[0]) + "_guard.xml"
        else:
            output = output[0].split(".")
            output = str(output[0]) + ".xml"
            output_guard = str(output[0]) + "_guard.xml"
        # writing output
        with open(output, "w") as f:
            f.write(final_str)
        with open(output_guard, "w") as f:
            f.write(guard_str)

    return


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Transform XML files to raw text.")
    parser.add_argument("-i", "--input", action="store", required=True, nargs=1, help="path to file to transform.")
    parser.add_argument("-o", "--output", action="store", nargs=1,
                        help="desired path to resulting filename. Default : input filename + '_out.xml | _guard.xml.'")
    args=parser.parse_args()

    make_text(input=args.input[0], output=args.output)