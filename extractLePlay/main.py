# -*- coding: utf-8 -*-

from io.input import make_the_soup
from io.output import make_out_filenames, write_output, make_string
from transform import simplify, sort, breakdown
from utils.utils import report_warnings


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Transform XML files to raw text.")
    parser.add_argument("-i", "--input", action="store", required=True, nargs=1, help="path to file to transform.")
    parser.add_argument("-o", "--output", action="store", nargs=1,
                        help="desired path to resulting filename. Default : input filename + '_out.xml | _guard.xml.'")
    args = parser.parse_args()

    filename_in = args.input[0]
    filename_out = args.output

    # first we read the XML ABBY file
    transformed_text = input.make_the_soup(filename_in)
    if transformed_text:
        # then we simplify the XML tree be sorting text and non-text blocks
    	transformed_text = simplify.rearrange(transformed_text)
        # then we sort out headers and signatures, which may raise warnings
    	transformed_text_guard, transformed_text, warning_headers, warning_signatures = sort.exclude_headers_signatures(transformed_text)
        # then we transform the tree to separate the tree structure from the physical structure of the text
    	transformed_text = breakdown.make_breakers(transformed_text)

        # raising warnings and creating output files
    	report_warnings(warning_headers, warning_signatures)
    	final_xml_str = make_string(transformed_text)
    	final_guard_str = make_string(transformed_text_guard)

    	out_xml_file, out_guard, out_txt_file = make_out_filenames(filename_in, filename_out)
    	write_output(out_xml_file, final_xml_str)
    	write_output(out_guard, final_guard_str)

        # make plain text output
        # - recompose paragraphs
        # - identify title
        # - add management of location within the article from titles and headers
