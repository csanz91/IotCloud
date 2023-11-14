from hashlib import sha1
import os
import time
import pickle
import collections
import functools
import shutil
import logging

logger = logging.getLogger(__name__)

cacheFolder = "../cache"


def clear_cache():

    if os.path.exists(cacheFolder):
        shutil.rmtree(cacheFolder)
    os.makedirs(cacheFolder)


def cache_disk(seconds=3600, cache_folder=cacheFolder):
    def doCache(f):
        def inner_function(*args, **kwargs):

            # calculate a cache key based on the decorated method signature
            key = sha1(
                (str(f.__module__) + str(f.__name__) + str(args) + str(kwargs)).encode(
                    "utf-8"
                )
            ).hexdigest()
            filepath = os.path.join(cache_folder, key)

            # verify that the cached object exists and is less than $seconds old
            if os.path.exists(filepath):
                modified = os.path.getmtime(filepath)
                age_seconds = time.time() - modified
                if seconds == 0 or age_seconds < seconds:
                    for retryNum in range(2):
                        try:
                            return pickle.load(open(filepath, "rb"))
                        except EOFError:
                            logger.error(f"EOFError. retry num {retryNum}")
                            time.sleep(.2)

            # call the decorated function...
            result = f(*args, **kwargs)

            # ... and save the cached object for next time
            pickle.dump(result, open(filepath, "wb"))

            return result

        return inner_function

    return doCache
