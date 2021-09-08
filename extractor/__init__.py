from .foo import FooIE

_ALL_CLASSES = [
	klass
	for name, klass in globals().items()
	if name.endswith('IE') and name != 'GenericIE'
]

def gen_extractor_classes():
    """ Return a list of supported extractors.
    The order does matter; the first extractor matched is the one handling the URL.
    """
    return _ALL_CLASSES

