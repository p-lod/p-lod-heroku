import html

# because dominate will stop on html
pyhtml = html

import os
import re

import pandas as pd

import dominate
from dominate.tags import *

from bs4 import BeautifulSoup

from flask import Flask
from flask import render_template
from flask import request
from flask import redirect, url_for, after_this_request

from string import Template

import markdown

import rdflib as rdf
from rdflib.plugins.stores import sparqlstore


ns = {"dcterms" : "http://purl.org/dc/terms/",
      "owl"     : "http://www.w3.org/2002/07/owl#",
      "rdf"     : "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
      "rdfs"    : "http://www.w3.org/2000/01/rdf-schema#" ,
      "p-lod"   : "urn:p-lod:id:" }

app = Flask(__name__)


# Connect to the remote triplestore with read-only connection
store = rdf.plugin.get("SPARQLStore", rdf.store.Store)(endpoint="http://52.170.134.25:3030/plod_endpoint/query",
                                                       context_aware = False,
                                                       returnFormat = 'json')
g = rdf.Graph(store)


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
    doc.head += meta(name="DC.identifier", content="urn:p-lod:id/%s" % plod)

@app.route('/p-lod/id/<path:identifier>')
def identifiers(identifier):
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
           } ORDER BY ?sortorder ?plabel""" % (identifier), initNs = ns)
    eresult_df = pd.DataFrame(eresult, columns = eresult.json['head']['vars']).set_index('p')
    
    eparts = g.query(
        """SELECT ?part ?label ?vfile ?sortorder
           WHERE {
              ?part ?sub_property  p-lod:%s .
              ?sub_property rdfs:subPropertyOf p-lod:is-part-of .
              OPTIONAL { ?part dcterms:title ?label . }
              ?part rdf:type ?type .
              OPTIONAL { ?part p-lod:visual-documentation-file ?vfile }
              OPTIONAL { ?part p-lod:sort-order ?sortorder }
           } ORDER BY ?type ?sortorder ?part""" % (identifier), initNs = ns)
        

    qt = Template("""
PREFIX plod: <urn:p-lod:id:>
PREFIX dcterms: <http://purl.org/dc/terms/>
SELECT ?title ?spatial_item WHERE { 
  plod:$identifier plod:spatially-within+ ?spatial_item  .
  OPTIONAL { ?spatial_item dcterms:title ?title . }
  }""")
    espatialancestors = g.query(qt.substitute(identifier = identifier))



    qt = Template("""
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX plod: <urn:p-lod:id:>

SELECT ?depiction ?within (COUNT(?depiction) as ?count) WHERE {
    BIND ( plod:$resource AS ?resource ) 
 
    ?resource ^plod:spatially-within+/^plod:created-on-surface-of/^plod:is-part-of* ?component .
    ?component a plod:artwork-component .

    # when this is part of the PALP interface, this clause can select "smallest 
    # clickable spatial unit" that will be shown to public via its own page
    ?component plod:is-part-of+/plod:created-on-surface-of/plod:spatially-within* ?within .
    ?within a plod:$within_resolution .

    ?component plod:depicts ?depiction .
    OPTIONAL { ?component plod:has-action ?action . }
    OPTIONAL { ?component plod:has-color  ?color  . }

} GROUP BY ?depiction ?within ORDER BY DESC(?count) ?depiction ?within LIMIT 30""")

    ehasart = g.query(qt.substitute(resource = identifier, within_resolution = 'space'))



    esameas = g.query(
        """SELECT ?url ?label
           WHERE {
              ?url owl:sameAs p-lod:%s .
              ?url rdfs:label ?label .
           }""" % (identifier), initNs = ns)
           
    eobjects = g.query(
        """SELECT ?s ?p ?slabel ?plabel 
           WHERE {
              ?s  ?p p-lod:%s .
              OPTIONAL { ?s rdfs:label ?rslabel }
              OPTIONAL { ?p rdfs:label ?rplabel }
              OPTIONAL { ?s dcterms:title ?dslabel }
              OPTIONAL { ?p dcterms:title ?dplabel }

              BIND ( COALESCE ( ?rslabel,?dslabel ) AS ?slabel )
              BIND ( COALESCE ( ?rplabel,?dplabel ) AS ?plabel )

              FILTER ( ?p != p-lod:next )
              FILTER ( ?p != p-lod:is-part-of )
              FILTER ( ?p != owl:sameAs )
           }  ORDER BY ?s LIMIT 100""" % (identifier), initNs = ns)

    edoc = dominate.document(title="Linked Open Data for Pompeii: %s" % (identifier))
    plodheader(edoc, identifier)
    
    edoc.body['prefix'] = "bibo: http://purl.org/ontology/bibo/  cc: http://creativecommons.org/ns#  dcmitype: http://purl.org/dc/dcmitype/  dcterms: http://purl.org/dc/terms/  foaf: http://xmlns.com/foaf/0.1/  nm: http://nomisma.org/id/  owl:  http://www.w3.org/2002/07/owl#  rdfs: http://www.w3.org/2000/01/rdf-schema#   rdfa: http://www.w3.org/ns/rdfa#  rdf:  http://www.w3.org/1999/02/22-rdf-syntax-ns#  skos: http://www.w3.org/2004/02/skos/core#"
    with edoc:
        with nav(cls="navbar navbar-default navbar-fixed-top"):
           with div(cls="container-fluid"):
               with div(cls="navbar-header"):
                   a("P-LOD Linked Open Data for Pompeii: Identifier Display and Browse", href="/p-lod/id/pompeii",cls="navbar-brand")
                   
                   with ul(cls="nav navbar-nav"):
                       with li(cls="dropdown"):
                           a("Go to...", href="#",cls="dropdown-toggle", data_toggle="dropdown")
                           with ul(cls="dropdown-menu", role="menu"):
                               li(a('Pompeii', href="/p-lod/id/pompeii"))
    
        with div(cls="container", about="/p-lod/%s" % (identifier)):
        
            with dl(cls="dl-horizontal"):
                unescapehtml = False
                dt()
                #if rdf.URIRef('http://www.w3.org/2000/01/rdf-schema#label') in eresult_df.index:
                #    c_title = eresult_df.loc[rdf.URIRef('http://www.w3.org/2000/01/rdf-schema#label'),'o']
                #else:
                c_title = identifier


                dd(strong(f"{c_title} [urn:p-lod:id:{identifier}]", cls="large"), style="margin-top:.5em;margin-bottom:.5em")
                

                for row in eresult:
                    if str(row.plabel) != 'None':
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
                            a(str(row.o),href = str(row.o).replace('urn:p-lod:id:',''))
                        elif str(row.o)[0:3] == 'urn':
                            a(row.o, title = str(row.o),href = str(row.o).replace('urn:p-lod:id:',''))
                        else:
                            span(olabel)  
                                
                        
                
        
                if len(esameas) > 0:
                    for row in esameas:
                        dt("Alternate identifier")
                        dd(str(row.url))

      
                if False: #len(eparts) > 0:
                    dt('Has parts')
                    with dd():
                        first = 0
                        curlabel = ''
                        for part in eparts:
                            label = str(part.part)
                            if curlabel != label:
                                curlabel = label
                                
                                if first == 1:
                                    first = 0
                                    pstyle = ''
                                else:
                                    pstyle = ''

                                p(a(label, rel="dcterms:hasPart", href = str(part.part).replace('urn:p-lod:id:','')), style=pstyle)  

                            if str(part.vfile) != "None":
                                thumb = str(part.vfile)
                                a(img(style="margin-left:1em;margin-bottom:15px;max-width:150px;max-height:150px",src=thumb),href=str(part.part).replace('urn:p-lod:id:',''))

            if len(espatialancestors) > 0:
                with dl(cls="dl-horizontal"):
                    dt('Spatial Ancestors', style="")
                    with dd():
                        first = 0
                        curlabel = ''
                        for ancestor in espatialancestors:
                            label = str(ancestor.spatial_item)
                            if curlabel != label:
                                curlabel = label
                                
                                if first == 1:
                                    first = 0
                                    pstyle = ''
                                else:
                                    pstyle = ''

                                span(a(label, rel="dcterms:hasPart", href = str(ancestor.spatial_item).replace('urn:p-lod:id:','')), style=pstyle)
                                br()
                 

            objlength = len(eobjects)
            if objlength: # objlength > 0:
                with dl(cls="dl-horizontal"):
                    lenstr = ''
                    if objlength == 1000:
                        lenstr = '(first 1000)'
                    dt(f"Used as Object By  {lenstr}")
                    with dd():
                         for s_p in eobjects:
                            a(str(s_p.s), href= str(s_p.s).replace('urn:p-lod:id:',''))
                            span(" via ")
                            span(str(s_p.p))
                            br()

            if len(ehasart) > 0:
                with dl(cls="dl-horizontal"):
                    dt('Artwork within (first 30)')

                    with dd():
                        first = 0
                        curlabel = ''
                        for art in ehasart:
                            label = str(art.depiction)
                            within = str(art.within)
                            if curlabel != label:
                                curlabel = label
                                
                                if first == 1:
                                    first = 0
                                    pstyle = ''
                                else:
                                    pstyle = ''

                                span(a(label, rel="dcterms:hasPart", href = str(art.depiction).replace('urn:p-lod:id:','')), style=pstyle)
                                br()
                          

                
        with footer(cls="footer"):
            with div(cls="container"):
                with p(cls="text-muted"):
                  with p():
                    span("Work on the Pompeii Linked Open Data (P-LOD) browser is currently undertaken as part of the Getty funded Pompeii Artistic Landscape Project. PALP is co-directed by Eric Poehler and Sebastian Heath.")
                    
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
                   a("P-LOD Linked Open Data for Pompeii: Vocabulary", href="/p-lod/id/pompeii",cls="navbar-brand")
                   with ul(cls="nav navbar-nav"):
                       with li(cls="dropdown"):
                           a("Browse", href="#",cls="dropdown-toggle", data_toggle="dropdown")
                           with ul(cls="dropdown-menu", role="menu"):
                               li(a('Go to Pompeii', href="/p-lod/id/pompeii"))

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
                span("Work on the Pompeii Linked Open Data (P-LOD) browser is currently undertaken as part of the Getty funded Pompeii Artistic Landscape Project. PALP is co-directed by Eric Poehler and Sebastian Heath.")
 
                 
    return vdoc.render()

@app.route('/')
def index():
    return redirect("/p-lod/id/pompeii", code=302)
    

    
