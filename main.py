import html

# because dominate will stop on html
pyhtml = html

import os
import re
#import urllib.parse
#import urllib.request

import dominate
from dominate.tags import *


from bs4 import BeautifulSoup

from flask import Flask
from flask import render_template
from flask import request
from flask import redirect, url_for, after_this_request

import markdown
import os

import rdflib as rdf
from rdflib_sqlalchemy import registerplugins


ns = {"dcterms" : "http://purl.org/dc/terms/",
      "owl"     : "http://www.w3.org/2002/07/owl#",
      "rdf"     : "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
      "rdfs"    : "http://www.w3.org/2000/01/rdf-schema#" ,
      "p-lod"   : "http://p-lod.umasscreate.net/vocabulary#",
      "p-lod-v" : "http://digitalhumanities.umass.edu/p-lod/vocabulary/",
      "p-lod-e" : "http://digitalhumanities.umass.edu/p-lod/entities/" }

app = Flask(__name__)


registerplugins()
store = rdf.plugin.get("SQLAlchemy", rdf.store.Store)(identifier="p-lod-store")
g = rdf.Graph(store, identifier="p-lod-graph")
g.open(rdf.Literal("sqlite:///%(here)s/p-lod-triplestore.sqlite" % {"here": os.getcwd()}),
       create = True)


# g = rdflib.Graph()


#result = g.parse("google-lod-triples.ttl", format="turtle")
#result = g.parse("google-spaces-and-features.ttl", format="turtle")
#result = g.parse("google-artwork-triples.ttl", format="turtle")

def plodheader(doc, plod = ''):
    
    # doc['xmlns'] = "http://www.w3.org/1999/xhtml" # Dominate doesn't produce closed no-content tags
    doc.head += meta(charset="utf-8")
    doc.head += meta(http_equiv="X-UA-Compatible", content="IE=edge")
    doc.head += meta(name="viewport", content="width=device-width, initial-scale=1")
    doc.head += link(rel='stylesheet', href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css",integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u",crossorigin="anonymous")
    doc.head += link(rel="stylesheet", href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap-theme.min.css", integrity="sha384-rHyoN1iRsVXV4nD0JutlnGaslCJuC7uwjduW9SVrLvRYooPp2bWYgmgJQIXwl/Sp", crossorigin="anonymous")
    doc.head += script(src="http://code.jquery.com/jquery-3.1.1.min.js")
    doc.head += script(src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js",integrity="sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa",crossorigin="anonymous")
    doc.head += style("body { padding-top: 60px; }")
    doc.head += meta(name="DC.title",lang="en",content="%s" % (plod) )
    doc.head += meta(name="DC.identifier", content="http://digitalhumanities.umass.edu/p-lod/%s" % plod)

@app.route('/p-lod/entities/<path:entity>')
def entities(entity):
    # @after_this_request
    # def add_header(response):
    #    response.headers['Content-Type'] = 'application/xhtml+xml; charset=utf-8'
    #    return response
         
    eresult = g.query(
        """SELECT ?p ?o ?plabel ?prange ?olabel ?sortorder
           WHERE {
              p-lod:%s ?p ?o .
              OPTIONAL { ?p rdfs:label ?plabel }
              OPTIONAL { ?p rdfs:range ?prange }
              OPTIONAL { ?p p-lod:sort-order ?sortorder }
              OPTIONAL { ?o rdfs:label ?olabel }
           } ORDER BY ?sortorder ?plabel""" % (entity), initNs = ns)

    elabel = g.query(
        """SELECT ?slabel 
           WHERE {
              p-lod:%s dcterms:title ?slabel
           }""" % (entity), initNs = ns)
           
    eparts = g.query(
        """SELECT ?part ?label ?vfile ?sortorder
           WHERE {
              ?part ?sub_property  p-lod:%s .
              ?sub_property rdfs:subPropertyOf p-lod:is-part-of .
              OPTIONAL { ?part dcterms:title ?label . }
              ?part rdf:type ?type .
              OPTIONAL { ?part p-lod:visual-documentation-file ?vfile }
              OPTIONAL { ?part p-lod:sort-order ?sortorder }
           } ORDER BY ?type ?sortorder ?part""" % (entity), initNs = ns)
           
    esameas = g.query(
        """SELECT ?url ?label
           WHERE {
              ?url owl:sameAs p-lod-e:%s .
              ?url rdfs:label ?label .
           }""" % (entity), initNs = ns)
           
    eobjects = g.query(
        """SELECT ?s ?p ?slabel ?plabel 
           WHERE {
              ?s  ?p p-lod-e:%s .
              OPTIONAL { ?s rdfs:label ?slabel }
              OPTIONAL { ?p rdfs:label ?plabel }
              FILTER ( ?p != p-lod:next )
              FILTER ( ?p != p-lod:is-part-of )
              FILTER ( ?p != owl:sameAs )
           }  ORDER BY ?s LIMIT 1000""" % (entity), initNs = ns)

    edoc = dominate.document(title="Linked Open Data for Pompeii: %s" % (entity))
    plodheader(edoc, entity)
    
    edoc.body['prefix'] = "bibo: http://purl.org/ontology/bibo/  cc: http://creativecommons.org/ns#  dcmitype: http://purl.org/dc/dcmitype/  dcterms: http://purl.org/dc/terms/  foaf: http://xmlns.com/foaf/0.1/  nm: http://nomisma.org/id/  owl:  http://www.w3.org/2002/07/owl#  rdfs: http://www.w3.org/2000/01/rdf-schema#   rdfa: http://www.w3.org/ns/rdfa#  rdf:  http://www.w3.org/1999/02/22-rdf-syntax-ns#  skos: http://www.w3.org/2004/02/skos/core#"
    with edoc:
        with nav(cls="navbar navbar-default navbar-fixed-top"):
           with div(cls="container-fluid"):
               with div(cls="navbar-header"):
                   a("P-LOD Linked Open Data for Pompeii: Entity", href="/p-lod/entities/pompeii",cls="navbar-brand")
                   with ul(cls="nav navbar-nav"):
                       with li(cls="dropdown"):
                           a("Browse", href="#",cls="dropdown-toggle", data_toggle="dropdown")
                           with ul(cls="dropdown-menu", role="menu"):
                               li(a('Go to Pompeii', href="/p-lod/entities/pompeii"))
                               li(a('All Classes', href="/p-lod/vocabulary/entity"))
                               li(a('All Properties', href="/p-lod/vocabulary/vocabulary-item"))
    
        with div(cls="container", about="/p-lod/%s" % (entity)):
        
            with dl(cls="dl-horizontal"):
                unescapehtml = False
                dt()
                for row in elabel:
                    dd(strong(str(row.slabel), cls="large"))
                    
                for row in eresult:
                    if str(row.p) == 'http://www.w3.org/2000/01/rdf-schema#label':
                        continue
                    elif str(row.plabel) != 'None':
                        dt(str(row.plabel))
                    else:
                        dt(i(str(row.p)))
                
                    with dd():
                        if str(row.olabel) != "None":
                            olabel = str(row.olabel)
                        else:
                            olabel = str(row.o)
                
                        if re.search(r'(\.png|\.jpg)$', row.o, flags= re.I):
                            img(src=row.o,style="max-width:350px")
                        elif str(row.o)[0:4] == 'http':
                            if 'http://p-lod.umasscreate.net/vocabulary#' in str(row.o):
                                a(olabel, title = str(row.o),href = str(row.o).replace('http://p-lod.umasscreate.net/vocabulary#',''))
                            else:
                                a(str(row.o),href = str(row.o).replace('http://p-lod.umasscreate.net/vocabulary#',''))
                        else:
                            if str(row.prange) == 'http://digitalhumanities.umass.edu/p-lod/vocabulary/markdown-literal':
                                unescapehtml = True
                                span( markdown.markdown(olabel),cls="unescapehtml")
                            else:
                                span(olabel)
                
        
                if len(esameas) > 0:
                    for row in esameas:
                        dt("Alternate identifier")
                        dd(str(row.url))

        
                # dt("Future permalink")
                # dd("http://digitalhumanities.umass.edu/p-lod/entities/%s" % (entity) )
      
                if len(eparts) > 0:
                    dt('Has parts')
                    with dd():
                        first = 0
                        curlabel = ''
                        for part in eparts:
                            label = str(part.label)
                            if curlabel != label:
                                curlabel = label
                                
                                if first == 1:
                                    first = 0
                                    pstyle = ''
                                else:
                                    pstyle = 'border-top: thin dotted #aaa;width:25%'

                                p(a(label, rel="dcterms:hasPart", href = str(part.part).replace('http://p-lod.umasscreate.net/vocabulary#','')), style=pstyle)
                            

                            if str(part.vfile) != "None":
                                thumb = str(part.vfile)
                                a(img(style="margin-left:1em;margin-bottom:15px;max-width:150px;max-height:150px",src=thumb),href=str(part.part).replace('http://p-lod.umasscreate.net/vocabulary#',''))
                
                objlength = len(eobjects)
                if objlength > 0:
                    lenstr = ''
                    if objlength == 1000:
                        lenstr = '(first 1000)'
                    dt("Property of %s" % (lenstr))
                    with dd():
                         for s_p in eobjects:
                            a(str(s_p.slabel), href= str(s_p.s).replace('http://digitalhumanities.umass.edu',''))
                            span(" via ")
                            span(str(s_p.plabel))
                            br()

                
        with footer(cls="footer"):
            with div(cls="container"):
                with p(cls="text-muted"):
                    span("P-LOD/PALP is under construction.")
                    a(" Github", href = "https://github.com/p-lod/p-lod")
                    # span(". Parse ")
                    # a('RDFa', href="http://www.w3.org/2012/pyRdfa/extract?uri=http://p-lod.herokuapp.com/p-lod/entities/%s" % (entity))
                    # span(".")
                    
    if unescapehtml == True:
        soup =  BeautifulSoup(edoc.render(), "html.parser") 
        for each_div in soup.find_all("span", class_="unescapehtml"):
            asoup = BeautifulSoup(pyhtml.unescape(str(each_div)),'html.parser')
            each_div.replace_with(asoup)
        return str(soup)
    else:
        return edoc.render()

                
@app.route('/p-lod/vocabulary/<path:vocab>')
def vocabulary(vocab):
    vresult = g.query(
        """SELECT ?p ?o ?plabel ?olabel
           WHERE {
              p-lod-v:%s ?p ?o .
              OPTIONAL { ?p rdfs:label ?plabel }
              OPTIONAL { ?o rdfs:label ?olabel }
           } ORDER BY ?plabel""" % (vocab), initNs = ns)

    vlabel = g.query(
        """SELECT ?slabel 
           WHERE {
              p-lod-v:%s rdfs:label ?slabel
           }""" % (vocab), initNs = ns)
           
    vinstances = g.query(
        """SELECT ?instance ?label ?vfile
           WHERE {
              ?instance rdf:type p-lod-v:%s .
              ?instance rdfs:label ?label .
              OPTIONAL { ?instance p-lod-v:visual-documentation-file ?vfile }
           } ORDER BY ?instance""" % (vocab), initNs = ns)
           
    vsubs = g.query(
        """SELECT ?sub ?label
           WHERE {
              ?sub rdfs:subClassOf|rdfs:subPropertyOf p-lod-v:%s .
              ?sub rdfs:label ?label .
           } ORDER BY ?label""" % (vocab), initNs = ns)
    
    vusage = g.query(
        """SELECT ?s ?o ?slabel ?olabel
           WHERE {
              ?s p-lod-v:%s ?o .
              OPTIONAL { ?s rdfs:label ?slabel }
              OPTIONAL { ?o rdfs:label ?olabel }
           } ORDER BY ?s ?o LIMIT 2000""" % (vocab), initNs = ns)    

    vdoc = dominate.document(title="Pompeii LOD: %s" % (vocab))
    plodheader(vdoc, vocab)

    with vdoc:

        with nav(cls="navbar navbar-default navbar-fixed-top"):
           with div(cls="container-fluid"):
               with div(cls="navbar-header"):
                   a("P-LOD Linked Open Data for Pompeii: Vocabulary", href="/p-lod/entities/pompeii",cls="navbar-brand")
                   with ul(cls="nav navbar-nav"):
                       with li(cls="dropdown"):
                           a("Browse", href="#",cls="dropdown-toggle", data_toggle="dropdown")
                           with ul(cls="dropdown-menu", role="menu"):
                               li(a('Go to Pompeii', href="/p-lod/entities/pompeii"))
                               li(a('All Classes', href="/p-lod/vocabulary/entity"))
                               li(a('All Properties', href="/p-lod/vocabulary/vocabulary-item"))

        with div(cls="container"):
            with dl(cls="dl-horizontal"):
                dt()
                for row in vlabel:
                    dd(strong(str(row.slabel), cls="large"))

                for row in vresult:
                    if str(row.p) == 'http://www.w3.org/2000/01/rdf-schema#label':
                        continue
                    elif str(row.plabel) != 'None':
                        dt(str(row.plabel)+":")
                    else:
                        dt(i(str(row.p)), style = "margin-left:.25em")
                
                    with dd():
                        if str(row.olabel) != "None":
                            olabel = str(row.olabel)
                        else:
                            olabel = str(row.o)
                
                        if str(row.o)[0:4] == 'http':
                            a(olabel,href = str(row.o).replace('http://digitalhumanities.umass.edu',''))
                        else:
                            span(olabel)
        
                if len(vinstances) > 0:
                    dt('Entities')
                    with dd():
                        first = 0
                        curlabel = ''

                        for instance in vinstances:
                            label = str(instance.label)
                            if curlabel != label:
                                curlabel = label
                                
                                if first == 1:
                                    first = 0
                                    pstyle = ''
                                else:
                                    pstyle = 'border-top: thin dotted #aaa;width:25%'

                                p(a(label, href = str(instance.instance).replace('http://digitalhumanities.umass.edu','')),style = pstyle)

                            if str(instance.vfile) != "None":
                                thumb = str(instance.vfile)
                                a(img(style="margin-left:1em;margin-bottom:15px;max-width:150px;max-height:150px",src=thumb),href=str(instance.instance).replace('http://digitalhumanities.umass.edu',''))

        
                if len(vsubs) > 0:
                    dt('Hierarchy')
                    with dd():
                        for sub in vsubs:
                            p(a(str(sub.label), href = str(sub.sub).replace('http://digitalhumanities.umass.edu','')))
                            
                if len(vusage) > 0:
                    dt('Used by')
                    with dd():
                        for use in vusage:
                            with p():
                                a(str(use.slabel), href = str(use.s).replace('http://digitalhumanities.umass.edu',''))
                                span(" ⇒ ", style="color:gray")
                                if str(use.olabel) != 'None':
                                    label = str(use.olabel)
                                else:
                                    label = str(use.o).replace('http://digitalhumanities.umass.edu','')
                                a(str(label), href = str(use.o).replace('http://digitalhumanities.umass.edu',''))
                            

            hr()
            with p():
                span("P-LOD is under construction and is overseen by Steven Ellis, Sebastian Heath and Eric Poehler. Data available on ")
                a("Github", href = "https://github.com/p-lod/p-lod-data")
                span(".")  
                 
    return vdoc.render()

@app.route('/api/geojson/<path:entity>')
def geojson_entity(entity):
        geojsonr = g.query(
        """SELECT ?lat ?long ?geojson
           WHERE {
              OPTIONAL { p-lod-e:%s p-lod-v:latitude ?lat ;
                                    p-lod-v:longitude ?long .
                         }
              OPTIONAL { p-lod-e:%s p-lod-v:geojson ?geojson }
           }""" % (entity, entity), initNs = ns)
        
        if len(geojsonr) > 0:
            for row in geojsonr:
                pass
                    

@app.route('/')
def index():
    return redirect("/p-lod/entities/pompeii", code=302)
    

    
