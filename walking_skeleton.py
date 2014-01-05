#!/usr/bin/python
"""
Parses an XML issue report exported from Jira, and generates an HTML walking skeleton view of it.
Activity names are either the epic summary up to the first colon, or the first word of the epic summary if there is no colon.

See:

    http://agileproductdesign.com/blog/the_new_backlog.html
"""

__version__ = "0.01"

import logging
import optparse
import sys
import xml.etree.ElementTree

class WalkingSkeleton:
    def __init__(self, xmlfile, log):

        self.title = None
        self.stories = []       # In "rank" order, ie. the order they came in the XML file
        self.activities = []    # Not sure that I'll need this
        self.stories_without_epics = []         # Only used during construction: how can I get rid of this?
        self.stories_without_epics_yet = []     # Only used during construction: how can I get rid of this?
        self.log = log
        self.log.debug("XML file: %s", xmlfile)

        tree = xml.etree.ElementTree.parse(xmlfile)
        rss = tree.getroot()
        channel = rss[0]
        self.title = channel.findall('title')[0].text
        for item in channel.findall('item'):
            if item.findall('type')[0].text == 'Epic':
                epic = Epic(self.log).from_xml_item(item)
                self.add_epic(epic)
            else:
                story = Story(self.log).from_xml_item(item)
                self.add_story(story)

        other = Activity('Other', self.log)
        self.activities.append(other)
        issues_without_epics = Epic(self.log)
        issues_without_epics.text = 'Stories without epics'
        other.add_epic(issues_without_epics)
        issues_without_epics.activity = other
        for story in self.stories_without_epics:
            issues_without_epics.add_story(story)
            story.epic = issues_without_epics

    def __str__(self):
        string = ''
        for activity in self.activities:
            string += str(activity)+'\n\n'
        return string.strip()

    def add_epic(self, epic):
        activityname = epic.text.split(':')[0]
        if activityname == epic.text:
            activityname = epic.text.split()[0]
        activity = None
        for activity in self.activities:
            if activity.text == activityname:
                break
            activity = None
        if not activity:
            activity = Activity(activityname, self.log)
            self.activities.append(activity)
        activity.add_epic(epic)
        epic.activity = activity

        for story in self.stories_without_epics_yet:
            if story.epickey == epic.key:
                epic.add_story(story)
                story.epic = epic
                #self.log.debug('    Story: '+story.key)
        for story in epic.stories:
            self.stories_without_epics_yet.remove(story)

    def get_epic_by_key(self, epickey):
        for activity in self.activities:
            for epic in activity.epics:
                if epic.key == epickey:
                    return epic
        return None

    def add_story(self, story):
        self.stories.append(story)
        if story.epickey:
            epic = self.get_epic_by_key(story.epickey)
            if epic:
                epic.add_story(story)
                story.epic = epic
            else:
                self.stories_without_epics_yet.append(story)
        else:
            self.stories_without_epics.append(story)

    def htmldoc(self, limit=None):
        htmldoc = HtmlSkeletonDoc(self.title, self.log)
        table = htmldoc.table

        epics_already_added = []
        epics_in_this_swimlane = []
        previous_column = 0
        for story in self.stories[0:(limit if limit else -1)]:
            new_epic = story.epic
            new_activity = new_epic.activity

            if new_epic in epics_in_this_swimlane:
                if new_epic != epics_in_this_swimlane[-1]:
                    table.add_swimlane('stories')
                    epics_in_this_swimlane = []
            else:
                epics_in_this_swimlane.append(new_epic)
                self.log.debug('   Epic: {}'.format(new_epic.text))

            if new_epic not in epics_already_added:
                column = len(epics_already_added)
                for (i, epic) in list(enumerate(epics_already_added)):
                    if epic.activity == new_activity:
                        column = i+1   # Add after this column
                table.add_column([new_activity, new_epic], column)
                epics_already_added[column:column] = [new_epic]
            self.log.debug('      Story: {}'.format(story.text))
            column = epics_already_added.index(new_epic)
            table.append_to_column(column, story)
            previous_column = column

        self.log.debug('\n')
        return htmldoc

# ------------------------------------- HTML --------------------------------------------------------------------------

class HtmlSkeletonDoc:
    def __init__(self, title, log):
        self.title = title
        self.log = log
        self.table = HtmlTable(self.log)
        self.table.add_row('Activity', closed=True)
        self.table.add_row('Epic', closed=True)
        self.table.add_swimlane('stories')

        self.header = """<html>
<head>
    <title>"""+self.title+"""</title>
    <style type="text/css">
        <!--
        td.Activity {
            text-align:left;
            font-size:1.2em;
            padding:10px 4px;
        }
        td.Epic {
            padding:4px;
            background-color:#FFD700;
        }
        td.Story {
            padding:4px;
            background-color:#87CEFA;
        }
        td.Capability {
            padding:4px;
            background-color:#63FF42;
        }
        td.TechnicalDebt {
            padding:4px;
            background-color:#FF5926;
        }
        td.Maintenance {
            padding:4px;
            background-color:#FF2222;
        }
        a#link {
            display: block;
            width: 100%;
            height: 100%;
            color: #000;
            text-decoration: none;
        }
        a#link:hover {
            background-color: #666;
            color: #FFF;
        }
        //-->
    </style>
</head>
"""

    def __str__(self):
        return self.header + '\n<body>\n<h1>' + self.title + '</h1>' + str(self.table) + '\n</body>\n'

class HtmlTable:
    """ Not a general-purpose HTML table.
        Simplifying assumption is that, with the exception of the activity and epic header-rows,
        All other rows are added in swim-lanes.
    """
    def __init__(self, log):
        self.log = log
        self.rows = []

    def __str__(self):
        return '<table>\n' + '\n'.join([str(row) for row in self.rows]) + '\n</table>'

    def add_row(self, htmlclass, closed=False):
        self.rows.append(HtmlTableRow(htmlclass, self.log, self.width(), closed))
        return len(self.rows)-1

    def add_swimlane(self, htmlclass):
        self.log.debug('\nNew swimlane')
        for row in self.rows:
            row.close()
        self.rows.append(HtmlTableSwimlane(htmlclass, self.log, self.width()))

    def width(self):
        width = 0
        for row in self.rows:
            width = max(width, row.width())
        return width

    def add_column(self, contents, column=False):
        rownum = 0
        for row in self.rows:
            content = contents[rownum] if rownum<len(contents) else None
            row.add_column(column, content)
            rownum += 1

    def append_to_column(self, column, story):
        for row in self.rows:
            if row.closed:
                continue
            else:
                # Major assumptions here:
                # 1. This is a swim-lane.
                # 2. It is the last one.
                row.append_to_column(column, story)
                return
        raise Exception('Fell off the end of the swimlanes')

class HtmlTableRow:
    def __init__(self, htmlclass, log, columns=0, closed=False):
        self.htmlclass = htmlclass
        self.log = log
        self.closed = closed
        # This is a row of empty cells
        self.cells = [HtmlTableCell(self, self.log)] * columns

    def __str__(self):
        consolidated_cells = []
        for thiscell in self.cells:
            if consolidated_cells:
                (prevcell, span) = consolidated_cells[-1:][0]
                if prevcell.get_text() == thiscell.get_text():
                    consolidated_cells[-1:] = [(prevcell, span+1)]
                else:
                    consolidated_cells += [(thiscell, 1)]
            else:
                consolidated_cells += [(thiscell, 1)]
        string = '<tr>\n   ' + '\n   '.join([cell.string(span) for (cell, span) in consolidated_cells]) + '\n</tr>'
        return string

    def width(self):
        return len(self.cells)

    def add_column(self, column, item=None):
        if not column:
            column = self.width()
        self.cells[column:column] = [HtmlTableCell(self, self.log, item=item)]

    def get_cell(self, column):
        return self.cells[column].item

    def set_cell(self, column, item):
        if not self.get_cell(column):
            self.cells[column] = HtmlTableCell(self, self.log, item=item)
        else:
            raise Exception('Cell already set')

    def close(self):
        self.closed = True

class HtmlTableSwimlane(HtmlTableRow):
    """ A row that contains other rows.
        Looks like any other row to the parent table.
    """
    def __init__(self, htmlclass, log, columns=0):
        self.htmlclass = htmlclass
        self.log = log
        self.closed = False
        self.rows = [HtmlTableRow(self.htmlclass, self.log, columns=columns)]

    def __str__(self):
        return '<tr>\n   ' + '\n   '.join([str(row) for row in self.rows]) + '\n</tr>'

    def width(self):
        width = 0
        for row in self.rows:
            width = max(width, row.width())
        return width

    def add_column(self, column, item=None):
        for row in self.rows:
            row.add_column(column, item=item)

    def set_cell(self, column, story):
        raise Exception("Can't set cells directly in swim-lanes")

    def append_to_column(self, column, story):
        for row in self.rows:
            if row.get_cell(column):
                continue
            else:
                row.set_cell(column, story)
                return
        newrow = HtmlTableRow(self.htmlclass, self.log, columns=self.width())
        newrow.set_cell(column, story)
        self.rows.append(newrow)

class HtmlTableCell:
    def __init__(self, row, log, item=None):
        self.row = row
        self.item = item

    def __str__(self):
        return self.string(1)

    def string(self, colspan):
        return '<td' \
                +(' class="'+self.item.type+'"' if self.item else '') \
                +(' colspan="{}"'.format(colspan) if colspan>1 else '') \
                +'>' \
                + (self.item.text if self.item else '') \
                + '</td>'

    def get_text(self):
        if self.item:
            return self.item.text
        else:
            return None

# ------------------------------------- Activities, Epics, Stories ----------------------------------------------------

class Item:
    def __init__(self, log):
        self.log = log
        self.key = None
        self.type = None
        self.url = None
        self.text = None

    def item_from_xml_item(self, item):
        self.key = item.find('key').text
        self.url = item.find('link').text
        self.text = item.find('summary').text.encode(errors='replace')
        #self.log.debug(self.key+': '+self.text)
        return self

    def __str__(self):
        return self.str_indent(0)
    def str_indent(self, indent):
        if not self.key:
            raise Exception('Keyless items must override str_indent()')
        return ' '*indent+self.key+': '+self.text

class Activity(Item):
    def __init__(self, text, log):
        Item.__init__(self, log)
        self.type = 'Activity'
        self.text = text
        self.epics = []

    def __str__(self):
        string = self.text+':'
        for epic in self.epics:
            string += '\n'+epic.str_indent(4)
        return string

    def add_epic(self, epic):
        self.epics.append(epic)

class Epic(Item):
    def __init__(self, log):
        Item.__init__(self, log)
        self.type = 'Epic'
        self.activity = None
        self.stories = []

    def from_xml_item(self, item):
        self.item_from_xml_item(item)
        self.stories = []
        for cf in item.iter('customfield'):
            if cf.attrib['key'] == 'com.pyxis.greenhopper.jira:gh-epic-label':
                self.text = cf.find('customfieldvalues').find('customfieldvalue').text
        return self

    def __str__(self):
        return self.str_indent(0)
    def str_indent(self, indent):
        if self.key:
            string = ' '*indent+self.key+': '+self.text+' (Epic)'
        else:
            string = ' '*indent+self.text
        for story in self.stories:
            string += '\n'+story.str_indent(indent+4)
        return string

    def add_story(self, story):
        self.stories.append(story)

class Story(Item):
    def from_xml_item(self, item):
        self.item_from_xml_item(item)
        self.type = item.find('type').text.replace(' ','')
        self.epickey = None     # Duplication here: "epickey" is the string, until such time as the epic is created
        self.epic = None
        for cf in item.iter('customfield'):
            if cf.attrib['key'] == 'com.pyxis.greenhopper.jira:gh-epic-link':
                self.epickey = cf.find('customfieldvalues').find('customfieldvalue').text
                #self.log.debug('    Epic: '+self.epickey)
                break
        return self

# ------------------------------------- Command-line options ----------------------------------------------------------

def parse_command_line_arguments():
   usage = "usage: %prog [options] input_file [output_file]\n" + __doc__

   option_list = [
      optparse.make_option("-l", "--limit", type="int", action="store", dest="limit",
                           help="limit the number of stories to be included in the generated table"),
      optparse.make_option("-q", "--quiet", action="store_const", const=logging.WARNING, dest="verbosity",
                           help="only warning or higher messages are printed to stderr"),
      optparse.make_option("-v", "--verbose", action="store_const", const=logging.DEBUG, dest="verbosity",
                           help="debug messages are printed to stderr"),
      optparse.make_option("-n", "--dryrun", action="store_true",
                           help="parse arguments but don't run the test"),
   ]

   parser = optparse.OptionParser(usage, version = __file__+' '+__version__, option_list = option_list)
   parser.set_defaults(limit=None, verbosity=logging.INFO, dryrun=False)
   (options, args) = parser.parse_args()

   # The option parser has dealt with all the optional arguments, GNU-style.
   # We now check for the correct number of remaining command-line arguments
   if len(args) < 1:
      print "Error: An input file must be specified"
      print usage
      parser.print_help()
      sys.exit(2)

   if len(args) > 2:
      print "Error: Too many arguments"
      print usage
      parser.print_help()
      sys.exit(2)

   return (options, args)

# ------------------------------------- main --------------------------------------------------------------------------

if __name__ == "__main__":

    (options, args) = parse_command_line_arguments()

    log = logging.getLogger("WalkingSkeleton")
    log.addHandler(logging.StreamHandler())
    log.setLevel(options.verbosity)

    # The rules for the normal command-line arguments were enforced in parse_command_line_arguments().
    # No need for further checking here - we can just use them
    xmlfile = args[0]
    if len(args) == 2:
        outputfile = args[1]
        sys.stdout = open(outputfile, 'w')
    else:
        outputfile = None

    skel = WalkingSkeleton(xmlfile, log)
    if options.verbosity == logging.DEBUG:
        sys.stderr.write('\n' + str(skel) + '\n')

    print skel.htmldoc(limit=options.limit)

