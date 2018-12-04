# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from termcolor import colored
import re
from copy import copy


def is_number(s):
    """Test if a string contains a number

    :param s: string
    :return: boolean
    """
    try:
        int(s)
        return True
    except ValueError:
        return False


def make_the_soup(filename):
    """Read an xml document and return its content as a bs4 object

    :param filename: filename
    :return: content of the document or False
    :rtype: bs4.BeautifulSoup or boolean
    """
    # Parsing the XML file with lxml-xml used to work but no longer does
    # We are therefore parsing the input file with HTML (lxml)
    # which implies the following modifications:
    # - empty elements are open/close
    # - attributes are all lowercase
    # - the tree begins with extra html/body/... elements
    try:
        with open(filename, "r") as f:
            text = f.read()
        soup = BeautifulSoup(text, "lxml")
    except Exception as e:
        print(colored("Error", "red", attrs=["bold"]), e)
    return soup


def report_warnings(warning_headers, warning_signatures):
    """Print warnings in terminal

    :param warning_headers: list of potentially missed headers
    :param warning_signatures: list of potentially missed signatures
    """
    for warn_id, warn_string in warning_headers:
        print(colored("WARNING:", "yellow", attrs=["reverse"]),
              "Might be a HEADER but was left in output : '%s':\n\t" % (warn_id),
              colored(warn_string, "white", attrs=["dark"]))
    for warn_id, warn_string in warning_signatures:
        print(colored("WARNING:", "yellow", attrs=["reverse"]),
              "Might be a SIGNATURE but was left in output : '%s':\n\t" % (warn_id),
              colored(warn_string, "white", attrs=["dark"]))


def make_out_filenames(name_input, name_output=False):
    """Create filenames for the output

    :param name_input: filename
    :type name_input: string
    :param name_output: filename
    :type name_output: string or Boolean
    :return: filenames
    :rtype: tuple
    """
    if not name_output:
        nin = name_input.split(".")
        out_xml = str(nin[0]) + "_out.xml"
        out_guard = str(nin[0]) + "_guard.xml"
        out_txt = str(nin[0]) + ".txt"
    else:
        nout = name_output[0].split(".")
        out_xml = str(nout[0]) + ".xml"
        out_guard = str(nout[0]) + "_guard.xml"
        out_txt = str(nout[0]) + ".txt"
    return out_xml, out_guard, out_txt


def write_output(filename, content):
    """ Write strings into documents

    :param filename: filename
    :type filename: string
    :param content: file content
    :type content: string
    """
    with open(filename, "w") as f:
        f.write(content)


def rearrange(soup):
    """Simplify XML ABBY structure and sort text blocks from other types of blocks

    :param soup: parsed XML tree
    :type soup: bs4.BeautifulSoup
    :return: parsed XML tree
    :rtype: bs4.BeautifulSoup
    """
    all_pages = soup.find_all("page")
    for page in all_pages:
        all_blocks = page.find_all("block")
        for block in all_blocks:
            # modify figure type blocks, including tables
            if block["blocktype"] != "Text":
                block.name = "figure"
                block["type"] = block["blocktype"]
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
                # finding a way around to delete tag named text
                # because tag.text means something to bs4
                all_tags = block.contents
                for tag in all_tags:
                    if tag.name == "text":
                        tag.decompose()
                # moving line elements right under par element
                all_lines = block.find_all("line")
                for line in all_lines:
                    all_formatting = line.find_all("formatting")
                    one_string = []
                    for formatting in all_formatting:
                        one_string.append(formatting.string)
                        formatting.decompose()
                    line.append(" ".join(one_string))
                block["type"] = "Text"
                del block["blockname"]
                block.name = "div"
    return soup


def exclude_headers_signatures(soup):
    """Sort headers and signatures from the body of text and give each element an id
    
    :param soup: parsed XML tree
    :rtype soup: bs4.BeautifulSoup
    :return: parsed XML trees and lists of warnings
    :rtype: tuple
    """
    guard = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><document xmlns="http://www.abbyy.com/FineReader_xml/FineReader10-schema-v1.xml" version="1.0" producer="timeUs"></document>"""
    guard_soup = BeautifulSoup(guard, "xml")

    all_pages = soup.find_all("page")
    warning_headers = []
    warning_signatures = []
    count_page = 0
    # reading each individual page and its content to create identifiers (page/div/p/line)
    for page in all_pages:
        count_page += 1
        page["id"] = "page%s" % count_page
        page_f = copy(page)
        page_f.clear()
        all_divs = page.find_all("div")
        count_div = 0
        # since elements from the header can be split over several lines, ps or even divs
        # were make a single string to gather everything that maybe part of the header
        # and clean it later in the program.
        header_string = ""
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
                    id_line = "page%s_d%s_p%s_l" % (count_page, count_div, count_p)
                    # testing the line : is it a header and needs to be taken out of the tree?
                    if int(line["b"]) < (int(page["height"]) * 0.12):
                        if "linespacing" in line.parent.attrs:
                            # for headers, lineSpacing value is normal comprehended between 390 and 750.
                            if (int(line.parent["linespacing"]) <= 750) and (int(line.parent["linespacing"]) >= 390):
                                line_f = line.extract()
                                line_f["type"] = "header"
                                p_f.append(line_f)
                                # giving page @pagenb when the pagenumber is fully OCR-ed
                                if line_f.string:
                                    if is_number(line_f.string):
                                        page["pagenb"] = line_f.string
                                        # !!
                                        # need a warning for incoherent page numbers
                                    else:
                                        header_string = header_string + line_f.string + " "
                        # raising warning if in the top 12% of the page and short enough
                        # (55 is, generally, the max length of the header)
                        # that is because the value of @lineSpacing is sometimes out of the normal range
                        # or because sometimes @lineSpacing does not exist
                            else:
                                count_line += 1
                                line["id"] = id_line + str(count_line)
                                test_str = line.string
                                if len(test_str.replace(" ", "")) < 55:
                                    warning_headers.append((line["id"], line.string))
                        else:
                            count_line += 1
                            line["id"] = id_line + str(count_line)
                            test_str = line.string
                            if len(test_str.replace(" ", "")) < 55:
                                warning_headers.append((line["id"], line.string))
                    # testing the line : is it a signature and needs to be taken out of the tree?
                    elif int(line["b"]) > (int(page["height"]) * 0.91):
                        if len(line.string.strip()) <= 2:
                            # considered a signature if in the last 9% of page height and extra short
                            line_f = line.extract()
                            line_f["type"] = "signature"
                            p_f.append(line_f)
                        elif len(line.string.strip()) >= 3 and len(line.string) < 5:
                            # raising warning if in the last 9% of page height but not short enough
                            # in case parasiting characters were recognized
                            count_line += 1
                            line["id"] = id_line + str(count_line)
                            warning_signatures.append((line["id"], line.string))
                        else:
                            count_line += 1
                            line["id"] = id_line + str(count_line)
                    else:
                        count_line += 1
                        line["id"] = id_line + str(count_line)
                if len(p_f.contents) > 0:
                    div_f.append(p_f)
            if len(div_f.contents) > 0:
                page_f.append(div_f)
        if len(header_string) > 0:
            page["pageheader"] = header_string
        guard_soup.document.append(page_f)
    return guard_soup, soup, warning_headers, warning_signatures


def make_breakers(soup):
    """Transform <page></page> into <pb/> and <line></line> in <lb/>

    :param soup: parsed XML tree
    :type soup: bs4.BeautifulSoup
    :return: parsed XML tree
    :rtype: bs4.BeautifulSoup
    """
    broken_soup = BeautifulSoup("<document></document>", "xml")
    all_pages = soup.find_all("page")

    for page in all_pages:
        new_pb = BeautifulSoup("<temp><pb/></temp>", "xml")
        att_page = page.attrs
        for k in att_page:
            new_pb.pb[k] = att_page[k]
        broken_soup.document.append(new_pb.pb)

        for cont_page in page.contents:
            if cont_page.name:
                if cont_page.name == "div":
                    new_div = BeautifulSoup("<temp><div></div></temp>", "xml")
                    att_div = cont_page.attrs
                    for k in att_div:
                        new_div.div[k] = att_div[k]
                    for cont_div in cont_page.contents:
                        if cont_div.name:
                            new_p = BeautifulSoup("<temp><p></p></temp>", "xml")
                            att_p = cont_div.attrs
                            for k in att_p:
                                new_p.p[k] = att_p[k]
                            all_lines = cont_div.find_all("line")
                            for line in all_lines:
                                new_lb = BeautifulSoup("<temp><lb/></temp>", "xml")
                                att_line = line.attrs
                                for k in att_line:
                                    new_lb.lb[k] = att_line[k]
                                new_p.p.append(new_lb.lb)
                                new_p.p.append(line.string)
                            new_div.div.append(new_p.p)
                    broken_soup.document.append(new_div.div)
                else:
                    broken_soup.document.append(cont_page)
    return broken_soup


def make_transformation(input, output=False):
    """ Perform transformation to raw text, adding markers

    :param input: name of file to transform
    :param output: name of output file to create
    :type input: string
    :type output: list if True
    :return:
    """
    # first we read the XML ABBY file
    transformed_text = make_the_soup(input)

    if transformed_text:
        # then we simplify the XML tree be sorting text and non-text blocks
        transformed_text = rearrange(transformed_text)
        # then we sort out headers and signatures, which may raise warnings
        transformed_text_guard, transformed_text, warning_headers, warning_signatures = exclude_headers_signatures(transformed_text)
        # then we transform the tree to separate the tree structure from the physical structure of the text
        transformed_text = make_breakers(transformed_text)

        # raising warnings and creating output files
        report_warnings(warning_headers, warning_signatures)
        final_xml_str = str(transformed_text.prettify())
        guard_str = str(transformed_text_guard.prettify())
        out_xml_file, output_guard, out_txt_file = make_out_filenames(input, output)
        write_output(out_xml_file, final_xml_str)
        write_output(output_guard, guard_str)

        # make plain text output
        # - recompose paragraphs
        # - identify title
        # - add management of location within the article from titles and headers
    return


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Transform XML files to raw text.")
    parser.add_argument("-i", "--input", action="store", required=True, nargs=1, help="path to file to transform.")
    parser.add_argument("-o", "--output", action="store", nargs=1,
                        help="desired path to resulting filename. Default : input filename + '_out.xml | _guard.xml.'")
    args = parser.parse_args()

    make_transformation(input=args.input[0], output=args.output)
