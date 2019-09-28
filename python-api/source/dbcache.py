import datetime
import random


class DBCache:
    """"""
 
    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.cache = {}
        self.max_cache_size = 1000
 
    #----------------------------------------------------------------------
    def __contains__(self, key):
        """
        Returns True or False depending on whether or not the key is in the 
        cache
        """
        key = self.getValidKey(key)
        return key in self.cache

    #----------------------------------------------------------------------
    def __getitem__(self, key):
        """
        Returns the element from the cache
        """

        key = self.getValidKey(key)
        
        return self.cache[key]['value']
 
    #----------------------------------------------------------------------
    def update(self, key, value):
        """
        Update the cache dictionary and optionally remove the oldest item
        """
        key = self.getValidKey(key)
        if key not in self.cache and len(self.cache) >= self.max_cache_size:
            self.remove_oldest()
 
        self.cache[key] = {'date_accessed': datetime.datetime.now(),
                           'value': value}

    def clearCache(self, key):
        key = self.getValidKey(key)
        try:
            del self.cache[key]
        except KeyError:
            pass
 
    #----------------------------------------------------------------------
    def remove_oldest(self):
        """
        Remove the entry that has the oldest accessed date
        """
        oldest_entry = None
        for key in self.cache:
            if oldest_entry is None:
                oldest_entry = key
            elif self.cache[key]['date_accessed'] < self.cache[oldest_entry][
                'date_accessed']:
                oldest_entry = key
        self.cache.pop(oldest_entry)
 
    #----------------------------------------------------------------------
    @property
    def size(self):
        """
        Return the size of the cache
        """
        return len(self.cache)

    #----------------------------------------------------------------------
    def getValidKey(self, key):
        return key.split("|")[-1]