import vhs

# -- Project information -----------------------------------------------------

project = 'Python VHS'
copyright = '2023, Tamika Nomara'
author = 'Tamika Nomara'
release = version = vhs.__version__

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.githubpages',
    'sphinx_vhs',
]

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinxawesome_theme'
