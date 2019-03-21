import xml.etree.ElementTree as etree
from lxml.etree import QName
import os.path, re
from itertools import chain
from yast import *

def fetch_admin_templates(fname):
    Policies = {}
    templates = []
    items = {}
    def itemizer(ref, items):
        if 'item' in items[ref].keys():
            return
        # First build dependant children
        if len(items[ref]['children']) > 0:
            for child_ref in items[ref]['children']:
                itemizer(child_ref, items)
        # Next build the Item
        children = [items[cr]['item'] for cr in items[ref]['children']]
        if 'displayName' in items[ref].keys():
            items[ref]['item'] = Item(Id(ref), items[ref]['displayName'], False, children)

    # Set a namespace for the tag, if present
    def set_ns(tag, namespace):
        return '{%s}%s' % (namespace, tag) if namespace else tag

    def fetch_attr(obj, attr, strings, namespace, presentations):
        val = obj.attrib[attr]
        m = re.match('\$\((\w*).(\w*)\)', val)
        if m and m.group(1) == 'string':
            val = strings.find(set_ns('string[@id="%s"]' % m.group(2), namespace)).text
        elif m and m.group(1) == 'presentation':
            val = presentations.find(set_ns('presentation[@id="%s"]' % m.group(2), namespace)).text
        return val

    fparts = os.path.splitext(fname)
    if fparts[-1].lower() == '.admx':
        admx = etree.fromstring(open(fname, 'r').read())
        admx_ns = QName(admx.tag).namespace
        dirname = os.path.dirname(fparts[0])
        basename = os.path.basename(fparts[0])
        adml_file = os.path.join(dirname, 'en-US', '%s.adml' % basename)
        if not os.path.exists(adml_file):
            adml_file = os.path.join(dirname, '%s.adml' % basename)
            if not os.path.exists(adml_file):
                raise ValueError('adml file not found for %s' % fname)
        adml = etree.fromstring(open(adml_file, 'r').read())
        adml_ns = QName(adml.tag).namespace
        resources = adml.find(set_ns('resources', adml_ns))
        strings = resources.find(set_ns('stringTable', adml_ns))
        presentations = resources.find(set_ns('presentationTable', adml_ns))
        policies = admx.find(set_ns('policies', admx_ns)).findall(set_ns('policy', admx_ns))
        parents = set([p.find(set_ns('parentCategory', admx_ns)).attrib['ref'] for p in policies])
        categories = admx.find(set_ns('categories', admx_ns)).findall(set_ns('category', admx_ns))
        for category in categories:
            disp = fetch_attr(category, 'displayName', strings, adml_ns, presentations)
            my_ref = category.attrib['name']
            parentCategory = category.find(set_ns('parentCategory', admx_ns))
            par_ref = parentCategory.attrib['ref'] if parentCategory else None

            if my_ref not in items.keys():
                items[my_ref] = {}
                items[my_ref]['children'] = []
            if par_ref and par_ref not in items.keys():
                items[par_ref] = {}
                items[par_ref]['children'] = [my_ref]
            elif par_ref:
                items[par_ref]['children'].append(my_ref)
            items[my_ref]['displayName'] = disp
        for ref in items.keys():
            itemizer(ref, items)
        refs = [items[r]['children'] for r in items.keys() if not 'item' in items[r].keys()]
        refs = chain.from_iterable(refs)
        for r in refs:
            templates.append(items[r]['item'])

        for parent in parents:
            Policies[parent] = {}
            Policies[parent]['file'] = '\\MACHINE\\Registry.pol'
            Policies[parent]['gpe_extension'] = None
            Policies[parent]['new'] = None
            Policies[parent]['add'] = None
            Policies[parent]['header'] = (lambda : ['Setting', 'Value'])
            Policies[parent]['values'] = \
                    (lambda conf, reg_key, key, desc, valstr, val_type, _input : {
                        'setting' : {
                            'order' : 0,
                            'title' : 'Setting',
                            'get' : key,
                            'set' : None,
                            'valstr' : (lambda v : v),
                            'input' : {
                                'type' : 'Label',
                                'options' : None,
                                'description' : desc,
                            },
                        },
                        'value' : {
                            'order' : 1,
                            'title' : key,
                            'get' : get_admx_value(conf, reg_key, key),
                            'set' : (lambda v : set_admx_value(conf, reg_key, key, v, val_type)),
                            'valstr' : (lambda v : valstr(v) if get_admx_configured(conf, reg_key, key) else 'Not configured'),
                            'input' : _input,
                        },
                    } )

            def policy_generator(conf):
                values = {}
                for policy in policies:
                    if policy.find('parentCategory').attrib['ref'] != parent:
                        continue
                    disp = fetch_attr(policy, 'displayName', strings, adml_ns, presentations)
                    desc = fetch_attr(policy, 'explainText', strings, adml_ns, presentations)
                    values[disp] = {}
                    val_type = None
                    elements = policy.find('elements')
                    defined = get_admx_configured(conf, policy.attrib['key'], disp)
                    if elements.find('text') is not None:
                        val_type = 'TextEntry'
                        val_str = (lambda v : v if v else '')
                    elif elements.find('decimal') is not None:
                        val_type = 'IntField'
                        val_str = (lambda v : v)
                    elif elements.find('boolean') is not None:
                        val_type = 'CheckBox'
                        val_str = (lambda v : 'Disabled' if int(v) == 0 else 'Enabled')
                    values[disp]['values'] = Policies[parent]['values'](
                        conf, policy.attrib['key'], disp, desc, val_str, val_type,
                        {
                            'type' : val_type,
                            'configurable' : True,
                            'options' : None,
                        },
                    )
                return values

            Policies[parent]['opts'] = policy_generator

        return templates
