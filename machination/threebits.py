"""Some replacements for things normally found in python 3.x"""
import functools
from collections import OrderedDict, namedtuple

_CacheInfo = namedtuple("CacheInfo", "hits misses maxsize currsize")

def lru_cache(maxsize=100):
    """replacement lru_cache

    shamelessly cribbed from the python 3.2 functools.lru_cache
    """
    # we don't actuall honour maxsize - it's only there to keep the API
    # compatible
    maxsize = None
    def decorating_function(user_function,
                            tuple=tuple,
                            sorted=sorted,
                            len=len,
                            KeyError=KeyError):
        info = {'hits': 0, 'misses': 0}
        kwd_mark = (object(),)   # separates positional and keyword args


        cache = dict()
        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            key = args
            if kwds:
                key += kwd_mark + tuple(sorted(kwds.items()))
            try:
                result = cache[key]
                info['hits'] += 1
                return result
            except KeyError:
                pass
            result = user_function(*args, **kwds)
            info['misses'] += 1
            cache[key] = result
            return result

        def cache_info():
            """Report cache statistics"""
            return _CacheInfo(info['hits'], info['misses'], maxsize, len(cache))

        def cache_clear():
            """Clear the cache and cache statistics"""
            cache.clear()
            info['hits'] = info['misses'] = 0

        wrapper.cache_clear = cache_clear
        wrapper.cache_info = cache_info
        return wrapper
    return decorating_function
