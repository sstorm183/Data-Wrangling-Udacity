#!/usr/bin/env python
# coding: utf-8

# In[1]:


import xml.etree.ElementTree as ET
import re
from collections import defaultdict
import csv
import codecs
import pprint
import cerberus
import schema


# In[2]:



#Use iterparse to iteratively step through each top level element
#Shape Element in to diffrent structures
# Update street names
# Write structes to csv




# Set global parameters


filename = "slc.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

SCHEMA = schema.Schema

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
street_types = defaultdict(int)

#Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


# In[3]:


# expeted street endings

expected = ["Street", "Avenue", "North","Boulevard", "Drive", "Circle","Court", "Place",
"Square", "Lane", "Road", "Parkway", "Plaza", "Highway", "South", "South",
"East"]


# In[4]:


#Mapped street endings with corrections
mapping = { "St": "Street", " St. ": "Street", "st":"Street","Rd.": "Road", "Rd":
"Road", "Ave": "Avenue",
"Ave.": "Avenue", "Av": "Avenue", "Dr": "Drive", "Dr.": "Drive", "Blvd":
"Boulevard",
"Blvd": "Boulevard", "Blvd.": "Boulevard", "Ct": "Court", "Ctr": "Center",
"Pl": "Place",
"Ln": "Lane", "rd":"Road", "RD": "Road", "rD":"Road", "RD":"Road","Cir":
"Circle",
"S": "South", "E":"East", "N.":"North", "N": "North", "Hwy" : "Highway",
"HWY" : "Highway", "Ppl":"Place", "Northboud":"North", "Plz":"Plaza",
"Pkwy.":"Parkway" }


# In[5]:


#Takes street tag and corrects endings as needed

def clean_element(tag_value, tag_key):
    if tag_key=='street': 
        street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
        full_addr = tag_value
        find = street_type_re.search(full_addr)
    
        if find:
            street_type = find.group()
            if street_type not in expected:
                if street_type in mapping:
                    tag_value = update_street_name(full_addr, mapping) 
    return tag_value




# In[6]:


# Replaces and corrects street names as needed
def update_street_name(name, mapping):
    street = street_type_re.search(name).group()
    name = name.replace(street, mapping[street])
    return name


# In[7]:


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    
    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []
    
    if element.tag == 'node':
        for primary in element.iter():
            for i in node_attr_fields:
                if i in primary.attrib:
                    node_attribs[i] = primary.attrib[i]
                    
        if len(element) !=0:
            for j in range(0, len(element)):
                childel = element[j]
            
                tag = {}
            
                if not PROBLEMCHARS.search(childel.attrib['k']):
                    tag["id"] = element.attrib["id"]
                    tag["type"] = default_tag_type
                    tag['value'] = childel.attrib['v']
                    if ":" in childel.attrib['k']:
                        key_and_val = childel.attrib['k'].split(':', 1)
                        tag["type"] = "key" and "val"[0]
                        tag["key"] = "key" and "val"[1]
                        if tag["type"] =='addr':
                            tag["value"] = clean_element (tag["value"],tag["key"])
                    else:
                        tag["key"] = childel.attrib['k']
                        if tag["type"] == 'addr':
                            tag["value"] = clean_element(tag["value"],tag["key"])
                tags.append(tag)
            return ({'node': node_attribs, 'node_tags': tags})   
  #----------------------------------------------------------------------------------------------------------  
    elif element.tag == 'way':
        for primary in element.iter():
            for i in way_attr_fields:
                if i in primary.attrib:
                    way_attribs[i] = primary.attrib[i]
                    
        if len(element) != 0:
            for index in range (0,len(element)):
                childel = element[index]
                tag = {}
                if childel.tag=='tag':
                    if not PROBLEMCHARS.search(childel.attrib['k']):
                        tag["id"] = element.attrib["id"]
                        tag["type"] = default_tag_type
                        tag["value"] =childel.attrib['v']
                        if ":" in childel.attrib['k']:
                            key_and_val = childel.attrib['k'].split(':',1)
                            tag["key"] = key_and_val[1]
                            tag["type"] = key_and_val[0]
                            if tag["type"] == 'addr':
                                tag["value"] = clean_element(tag["value"],tag["key"])
                        else:
                            tag["key"] = childel.attrib['k']
                            if tag["type"] == 'addr':
                                tag["value"]=clean_element(tag["value"],tag["key"])
                    tags.append(tag)
            
            
                elif childel.tag=='nd':
                    way_node={}
                    way_node['id'] = element.attrib['id']
                    way_node['node_id'] = childel.attrib['ref']
                    way_node['position'] = index
                    
                    way_nodes.append(way_node)
            
        return ({'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags})


# In[8]:


def get_element(osm_file, tags=('node', 'way', 'relation')):
    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()
            


# In[9]:


def validate_element(element, validator, schema=SCHEMA):
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        raise Exception(message_string.format(field, error_string))


# In[10]:


class UnicodeDictWriter(csv.DictWriter, object):
    def writerow(self, row):
       super(UnicodeDictWriter, self).writerow({
           k: v for k, v in row.items()
       })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
            
    


# In[11]:


# Writes corrections to csv for sql import

def process_map(file_in, validate):
    with codecs.open(NODES_PATH, 'w', "utf-8") as nodes_file,    codecs.open(NODE_TAGS_PATH, 'w', "utf-8") as nodes_tags_file,    codecs.open(WAYS_PATH, 'w', "utf-8") as ways_file,    codecs.open(WAY_NODES_PATH, 'w', "utf-8") as way_nodes_file,    codecs.open(WAY_TAGS_PATH, 'w', "utf-8") as way_tags_file:
        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)
        
        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()
        
        validator = cerberus.Validator()
        
        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)
                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])
                    
            






        


# In[12]:


if __name__ == '__main__':
    process_map(filename, validate=False)


# In[13]:


import sqlite3
import csv
from pprint import pprint
import pandas as pd 


# In[14]:


sql_file = 'slc.db'


# In[15]:


conn = sqlite3.connect(sql_file)
c = conn.cursor()


# In[16]:


c.execute(''' DROP TABLE IF EXISTS nodes''')
c.execute(''' DROP TABLE IF EXISTS nodes_tags''')
c.execute(''' DROP TABLE IF EXISTS ways''')
c.execute(''' DROP TABLE IF EXISTS ways_tags''')
c.execute(''' DROP TABLE IF EXISTS ways_nodes''')


# In[17]:


conn.commit()


# In[18]:


c.execute('''CREATE TABLE nodes (id INTEGER PRIMARY KEY NOT NULL, lat REAL, lon REAL, user TEXT, uid INTEGER,version INTEGER,
    changeset INTEGER, timestamp TEXT) ''')

c.execute('''CREATE TABLE nodes_tags (id INTEGER, key TEXT, value TEXT, type TEXT, FOREIGN KEY (id) REFERENCES nodes(id)) ''')

c.execute('''CREATE TABLE ways (id INTEGER PRIMARY KEY NOT NULL, user TEXT, uid INTEGER, version TEXT, changeset INTEGER,
    timestamp TEXT)''')

c.execute('''CREATE TABLE ways_tags (id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, type TEXT,
    FOREIGN KEY (id) REFERENCES ways(id))''')

c.execute('''CREATE TABLE ways_nodes (id INTEGER NOT NULL, node_id INTEGER NOT NULL, position INTEGER NOT NULL,
    FOREIGN KEY (id) REFERENCES ways(id), FOREIGN KEY (node_id) REFERENCES nodes(id))''')


# In[19]:


conn.commit()


# In[20]:


nodes=pd.read_csv('nodes.csv')

nodes_tags=pd.read_csv('nodes_tags.csv')

ways=pd.read_csv('ways.csv')

ways_nodes=pd.read_csv('ways_nodes.csv')

ways_tags=pd.read_csv('ways_tags.csv')


# In[21]:


nodes.to_sql('nodes',conn,if_exists='append', index=False)

nodes_tags.to_sql('nodes_tags',conn,if_exists='append', index=False)

ways.to_sql('ways',conn,if_exists='append', index=False)

ways_nodes.to_sql('ways_nodes',conn,if_exists='append', index=False)

ways_tags.to_sql('ways_tags',conn,if_exists='append', index=False)


# In[22]:


conn.commit()


# In[ ]:




