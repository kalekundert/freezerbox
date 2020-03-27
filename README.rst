***********
PhosphateDB
***********

.. image:: https://img.shields.io/pypi/v/po4.svg
   :target: https://pypi.python.org/pypi/po4

.. image:: https://img.shields.io/pypi/pyversions/po4.svg
   :target: https://pypi.python.org/pypi/po4

.. image:: https://img.shields.io/readthedocs/phosphatedb.svg
   :target: https://phosphatedb.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/travis/kalekundert/phosphatedb.svg
   :target: https://travis-ci.org/kalekundert/phosphatedb

.. image:: https://img.shields.io/coveralls/kalekundert/phosphatedb.svg
   :target: https://coveralls.io/github/kalekundert/phosphatedb

PhosphateDB (or PO₄ for short) is a tool for keeping track of DNA constructs 
such as plasmids, gene fragments, and oligos.  It emphasizes keeping track of 
*how* each construct was made, and aims to be compatible with existing 
plasmid-management systems.

The name "PhosphateDB" is based on the fact that DNA molecules are held 
together by a phosphate backbone, and that the synthesis of new DNA is greatly 
facilitated by the chemical properties of phosphate.  Similarly, this database 
system aspires to robustly "hold together" DNA sequences in such a way that new 
sequences can easily be added and shared.

Example
=======
- Your want a tool to better manage your plasmids, but you don't want to spend 
  a bunch of time re-entering the information for your existing plasmids, which 
  is stored in a big Excel spreadsheet.  After installing PO₄, you quickly  
  configure it to recognize the column headers in your spreadsheet.  Nothing 
  about your existing spreadsheet needs to change.

- You just designed primers to clone a new plasmid.  You enter both the primers 
  and the plasmid into your spreadsheet.  While it's fresh in your head, you 
  also describe how the plasmid will be made in a column labeled 
  "Construction".  The description might look like::

      INV: template=p2 primers=o2,o3

  This syntax indicates that the plasmid is constructed by inverse PCR ("INV") 
  using the plasmid "p2" as a template and the oligos "o1" and "o2" as primers.

- You just received the primers you designed last week, but you don't remember 
  exactly how you were planning to use them.  You use PO₄---in conjunction with 
  `stepwise <https://github.com/kalekundert/stepwise>`__---to generate an 
  protocol specifying all the relevant details: volumes, concentrations, 
  construct names, etc.  If you are making several constructs, the protocol 
  will even group similar constructs and create master mixes of common reagents 
  when possible::

      $ stepwise make p3
      March 27, 2020

      $ stepwise make p3

      1. Prepare 10x primer mix [1]:

         Reagent   Stock    Volume
         ─────────────────────────
         o2       100 µM   0.50 µL
         o3       100 µM   0.50 µL
         water             9.00 µL
         ─────────────────────────
                          10.00 µL

      2. Setup 1 PCR reaction and 1 negative control [2]:

         Reagent           Stock    Volume
         ─────────────────────────────────
         water                     3.00 µL
         p2             20 pg/µL   1.00 µL
         primer mix          10x   1.00 µL
         Q5 master mix        2x   5.00 µL
         ─────────────────────────────────
                                  10.00 µL

      3. Run the following thermocycler protocol:

         - 98°C for 30s
         - Repeat 35x:
           - 98°C for 10s
           - 60°C for 20s
           - 72°C for 3 min
         - 72°C for 2 min

      4. Run 1 ligation reaction:

         Reagent              Stock    Volume
         ────────────────────────────────────
         water                        6.75 µL
         T4 ligase buffer       10x   1.00 µL
         T4 PNK             10 U/µL   0.25 µL
         T4 DNA ligase     400 U/µL   0.25 µL
         DpnI               20 U/µL   0.25 µL
         PCR product       50 ng/µL   1.50 µL
         ────────────────────────────────────
                                     10.00 µL

         - Incubate at room temperature for 1h.

      Notes:
      [1] For resuspending lyophilized primers:
          100 µM = 10 µL/nmol

      [2] For diluting template DNA to 20 pg/µL:
          Dilute 1 µL twice into 7*sqrt(DNA) µL

Installation
============
Install PO₄ using ``pip``::

    $ pip install po4

Usage
=====
More details coming soon...
