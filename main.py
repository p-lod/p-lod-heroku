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
    
    # as subject w/additional info
    qt =  Template("""SELECT ?p ?o ?plabel ?prange ?olabel
           WHERE {
              p-lod:$identifier ?p ?o .
              OPTIONAL { ?p rdfs:label ?plabel }
              OPTIONAL { ?o rdfs:label ?olabel }

           } ORDER BY ?plabel""")
    id_as_subject = g.query(qt.substitute(identifier = identifier), initNs = ns)
    id_as_subject_df = pd.DataFrame(id_as_subject, columns = id_as_subject.json['head']['vars']).set_index('p')
        
    # as object
    qt = Template("""SELECT ?s ?p 
           WHERE {
              ?s  ?p p-lod:$identifier .
           }  ORDER BY ?s LIMIT 100""")
    id_as_object = g.query(qt.substitute(identifier = identifier), initNs = ns)


    # as predicate
    qt = Template("""SELECT ?s ?o 
           WHERE {
              ?s p-lod:$identifier ?o  .
           }  ORDER BY ?s LIMIT 100""") 
    id_as_predicate = g.query(qt.substitute(identifier = identifier), initNs = ns)


    # spatial ancestors
    qt = Template("""
PREFIX plod: <urn:p-lod:id:>
SELECT ?title ?spatial_item WHERE { 
  plod:$identifier plod:spatially-within+ ?spatial_item  .
  }""")
    id_spatial_ancestors = g.query(qt.substitute(identifier = identifier))


    # has_art
    qt = Template("""
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX plod: <urn:p-lod:id:>

SELECT ?depiction ?within (COUNT(?depiction) as ?count) WHERE {
    BIND ( plod:$identifier AS ?resource ) 
 
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
    id_has_art = g.query(qt.substitute(identifier = identifier, within_resolution = 'space'))


    


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
                #if rdf.URIRef('http://www.w3.org/2000/01/rdf-schema#label') in id_as_subject_df.index:
                #    c_title = id_as_subject_df.loc[rdf.URIRef('http://www.w3.org/2000/01/rdf-schema#label'),'o']
                #else:
                # c_title = identifier

                dd(strong(identifier, cls="large"), style="margin-top:.5em;margin-bottom:.5em")

                for row in id_as_subject:
                    if str(row.plabel) != 'None':
                        with dt():
                          a(str(row.plabel), href = str(row.p).replace('urn:p-lod:id:',''))
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
    
            if len(id_spatial_ancestors) > 0:
                with dl(cls="dl-horizontal"):
                    dt('Spatial Ancestors', style="")
                    with dd():
                        for ancestor in id_spatial_ancestors:
                            label = str(ancestor.spatial_item)
                            span(a(label, rel="dcterms:hasPart", href = str(ancestor.spatial_item).replace('urn:p-lod:id:','')))
                            br()
                 
            objlength = len(id_as_object)
            if objlength: # objlength > 0:
                with dl(cls="dl-horizontal"):
                    lenstr = ''
                    if objlength == 1000:
                        lenstr = '(first 1000)'
                    dt(f"Used as Object By {lenstr}")
                    with dd():
                         for s_p in id_as_object:
                            a(str(s_p.s), href= str(s_p.s).replace('urn:p-lod:id:',''))
                            span(" via ")
                            a(str(s_p.p),href = str(s_p.p).replace('urn:p-lod:id:',''))
                            br()

            predlength = len(id_as_predicate)
            if predlength: # objlength > 0:
                with dl(cls="dl-horizontal"):
                    lenstr = ''
                    if predlength == 1000:
                        lenstr = '(first 1000)'
                    dt(f"Used as Predicate By {lenstr}")
                    with dd():
                         for s_o in id_as_predicate:
                            a(str(s_o.s), href= str(s_o.s).replace('urn:p-lod:id:',''))
                            span(" → ")
                            a(str(s_o.o),href = str(s_o.o).replace('urn:p-lod:id:',''))
                            br()

            if len(id_has_art) > 0:
                with dl(cls="dl-horizontal"):
                    dt('Artwork within (first 30)')

                    with dd():
                        for art in id_has_art:
                            label = str(art.depiction)
                            span(a(label, rel="dcterms:hasPart", href = str(art.depiction).replace('urn:p-lod:id:','')))
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


@app.route('/')
def index():
    return redirect("/p-lod/id/pompeii", code=302)
    

    
