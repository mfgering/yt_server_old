import sys

p = 'c:\\Python\\yt_server\\youtube_dl'
sys.path.append(p)
sp = sys.path
import extractors.hclips
#import youtube_dl.youtube_dl.YoutubeDL
import test.test_download
import unittest

unittest.main()
print("done")