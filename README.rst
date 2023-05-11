wikimapper
==========

.. image:: https://img.shields.io/pypi/l/wikimapper.svg
  :alt: PyPI - License
  :target: https://pypi.org/project/wikimapper/

.. image:: https://img.shields.io/pypi/pyversions/wikimapper.svg
  :alt: PyPI - Python Version
  :target: https://pypi.org/project/wikimapper/

.. image:: https://img.shields.io/pypi/v/wikimapper.svg
  :alt: PyPI
  :target: https://pypi.org/project/wikimapper/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
  :target: https://github.com/ambv/black  

This small Python library helps you to map Wikipedia page titles (e.g. `Manatee
<https://en.wikipedia.org/wiki/Manatee>`_ to `Q42797 <https://www.wikidata.org/wiki/Q42797>`_)
and vice versa. This is done by creating an index of these mappings from a Wikipedia SQL dump.
Precomputed indices can be found under `Precomputed indices`_. Redirects are taken into account.

Installation
------------

This package can be installed via ``pip``, the Python package manager.

.. code:: bash

    pip install wikimapper

If all you want is just mapping, then you can also just download ``wikimapper/mapper.py`` and
add it to your project. It does not have any external dependencies.

Usage
-----

Using the mapping functionality requires a precomputed index. It is created from Wikipedia
SQL dumps (see `Create your own index`_) or can be downloaded for certain languages
(see `Precomputed indices`_). For the following to work, it is assumed that an index either
has been created or downloaded. Using the command line for batch mapping is not recommended,
as it requires repeated opening and closing the database, leading to a speed penalty.

Map Wikipedia page title to Wikidata id
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from wikimapper import WikiMapper

    mapper = WikiMapper("index_enwiki-latest.db")
    wikidata_id = mapper.title_to_id("Python_(programming_language)")
    print(wikidata_id) # Q28865

or from the command line via

.. code:: bash

    $ wikimapper title2id index_enwiki-latest.db Germany
    Q183

Map Wikipedia URL to Wikidata id
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from wikimapper import WikiMapper

    mapper = WikiMapper("index_enwiki-latest.db")
    wikidata_id = mapper.url_to_id("https://en.wikipedia.org/wiki/Python_(programming_language)")
    print(wikidata_id) # Q28865

or from the command line via

.. code:: bash

    $ wikimapper url2id index_enwiki-latest.db https://en.wikipedia.org/wiki/Germany
    Q183

It is not checked whether the URL origins from the same Wiki as the index you created!

Map Wikidata id to Wikipedia page title
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from wikimapper import WikiMapper

    mapper = WikiMapper("index_enwiki-latest.db")
    titles = mapper.id_to_titles("Q183")
    print(titles) # Germany, Deutschland, ...

or from the command line via

.. code:: bash

    $ wikimapper id2titles data/index_enwiki-latest.db Q183
    Germany
    Bundesrepublik_Deutschland
    Land_der_Dichter_und_Denker
    Jerman
    ...

Mapping id to title can lead to more than one result, as some pages in Wikipedia are
redirects, all linking to the same Wikidata item.

Map Wikipedia id to Wikidata id
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from wikimapper import WikiMapper

    mapper = WikiMapper("index_enwiki-latest.db")
    wikidata_id = mapper.wikipedia_id_to_id(3342)
    print(wikidata_id)  # Q183


Map Wikidata id to Wikipedia id
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from wikimapper import WikiMapper

    mapper = WikiMapper("index_enwiki-latest.db")
    wikipedia_ids = mapper.id_to_wikipedia_ids("Q183")
    print(wikipedia_ids)  # [3342, 10590, 11833, 11840, ...]

Mapping Wikidata id to Wikipedia id can lead to more than one result, as some pages in Wikipedia are
redirects, all linking to the same Wikidata item.

Map Wikipedia id to Wikipedia page title
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from wikimapper import WikiMapper

    mapper = WikiMapper("index_enwiki-latest.db")
    page_title = mapper.wikipedia_id_to_title(3342)
    print(page_title)  # Bundesrepublik_Deutschland

Map Wikipedia page title to Wikipedia id
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from wikimapper import WikiMapper

    mapper = WikiMapper("index_enwiki-latest.db")
    wikipedia_id = mapper.title_to_wikipedia_id("Germany")
    print(wikipedia_id)  # 11867

Create your own index
~~~~~~~~~~~~~~~~~~~~~

While some indices are precomupted, it is sometimes useful to create your own. The
following section describes the steps need. Regarding creation speed: The index creation
code works, but is not optimized. It takes around 10 minutes on my Notebook (T480s)
to create it for English Wikipedia if the data is already downloaded.

**1. Download the data**

The easiest way is to use the command line tool that ships with this package. It
can be e.g. invoked by

.. code:: bash

    $ wikimapper download enwiki-latest --dir data

Use ``wikimapper download --help`` for a full description of the tool.

The abbreviation for the Wiki of your choice can be found on `Wikipedia
<https://en.wikipedia.org/wiki/List_of_Wikipedias>`_. Available SQL dumps can be
e.g. found on `Wikimedia <https://dumps.wikimedia.org/>`_, you need to suffix
the Wiki name, e.g. ``https://dumps.wikimedia.org/dewiki/`` for the German one.
If possible, use a different mirror than the default in order to spread the resource usage.

**2. Create the index**

The next step is to create an index from the downloaded dump. The easiest way is to use
the command line tool that ships with this package. It can be e.g. invoked by

.. code:: bash

    $ wikimapper create enwiki-latest --dumpdir data --target data/index_enwiki-latest.db

This creates an index for the previously downloaded dump and saves it in ``data/index_enwiki-latest.db``.
Use ``wikimapper create --help`` for a full description of the tool.

Precomputed indices
-------------------

.. _precomputed:

Several precomputed indices can be found `here <https://public.ukp.informatik.tu-darmstadt.de/wikimapper/>`_ .

Command line interface
----------------------

This package comes with a command line interface that is automatically available
when installing via ``pip``. It can be invoked by ``wikimapper`` from the command
line.

::

    $ wikimapper

    usage: wikimapper [-h] [--version]
                      {download,create,title2id,url2id,id2titles} ...

    Map Wikipedia page titles to Wikidata IDs and vice versa.

    positional arguments:
      {download,create,title2id,url2id,id2titles}
                            sub-command help
        download            Download Wikipedia dumps for creating a custom index.
        create              Use a previously downloaded Wikipedia dump to create a
                            custom index.
        title2id            Map a Wikipedia title to a Wikidata ID.
        url2id              Map a Wikipedia URL to a Wikidata ID.
        id2titles           Map a Wikidata ID to one or more Wikipedia titles.

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program's version number and exit

See ``wikimapper ${sub-command} --help`` for more information.

Development
-----------

The required dependencies are managed by **pip**. A virtual environment
containing all needed packages for development and production can be
created and activated by

::

    virtualenv venv --python=python3 --no-site-packages
    source venv/bin/activate
    pip install -e ".[test, dev, doc]"

The tests can be run in the current environment by invoking

::

    make test

or in a clean environment via

::

    tox

FAQ
---

How does the parsing of the dump work?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`jamesmishra <https://github.com/jamesmishra/mysqldump-to-csv>`__ has noticed that
SQL dumps from Wikipedia almost look like CSV. He provides some basic functions
to parse insert statements into tuples. We then use the Wikipedia SQL page
dump to get the mapping between title and internal id, page props to get
the Wikidata ID for a title and then the redirect dump in order to fill
titles that are only redirects and do not have an entry in the page props table.

Why do you not use the Wikidata SPARQL endpoint for that?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to query the official Wikidata SPARQL endpoint to do the mapping:

.. code:: sparql

    prefix schema: <http://schema.org/>
    SELECT * WHERE {
      <https://en.wikipedia.org/wiki/Manatee> schema:about ?item .
    }

This has several issues: First, it uses the network, which is slow. Second, I try to use
that endpoint as infrequent as possible to save their resources (my use case is to map
data sets that have easily tens of thousands of entries). Third, I had coverage issues due
to redirects in Wikipedia not being resolved (around ~20% of the time for some older data sets).
So I created this package to do the mapping offline instead.

Acknowledgements
----------------

I am very thankful for `jamesmishra <https://github.com/jamesmishra>`__  to provide
`mysqldump-to-csv <https://github.com/jamesmishra/mysqldump-to-csv>`__ . Also,
`mbugert <https://github.com/mbugert>`__ helped me tremendously understanding
Wikipedia dumps and giving me the idea on how to map.
