#!/usr/bin/env python
"""
Tests for eups.Eups
"""

import pdb                              # we may want to say pdb.set_trace()
import os
import sys
import unittest
import time
from testCommon import testEupsStack

from eups import TagNotRecognized, Product, ProductNotFound
from eups.Eups import Eups
from eups.stack import ProductStack
from eups.utils import Quiet

class EupsTestCase(unittest.TestCase):

    def setUp(self):
        os.environ["EUPS_PATH"] = testEupsStack
        os.environ["EUPS_FLAVOR"] = "Linux"
        self.dbpath = os.path.join(testEupsStack, "ups_db")
        self.eups = Eups()

        self.betachain = os.path.join(self.dbpath,"python","beta.chain")

    def testDefCtor(self):
        pass

    def tearDown(self):
        flavors = self.eups.versions[testEupsStack].getFlavors()
        for flav in flavors:
            file = os.path.join(self.dbpath, ProductStack.persistFilename(flav))
            if os.path.exists(file):
                os.remove(file)

        if os.path.exists(self.betachain):  os.remove(self.betachain)

        newprod = os.path.join(self.dbpath,"newprod")
        if os.path.exists(newprod):
            for dir,subdirs,files in os.walk(newprod, False):
                for file in files:
                    os.remove(os.path.join(dir,file))
                for file in subdirs:
                    os.rmdir(os.path.join(dir,file))
            os.rmdir(newprod)
                    

    def testInit(self):
        self.assertEquals(len(self.eups.path), 1)
        self.assertEquals(self.eups.path[0], testEupsStack)
        self.assertEquals(self.eups.getUpsDB(testEupsStack), self.dbpath)
        self.assertEquals(len(self.eups.versions.keys()), 1)
        self.assert_(self.eups.versions.has_key(testEupsStack))
        self.assert_(self.eups.versions[testEupsStack] is not None)

        flavors = self.eups.versions[testEupsStack].getFlavors()
        self.assertEquals(len(flavors), 3)
        for flav in "Linux64 Linux Generic".split():
            self.assert_(flav in flavors)

        # 2 default tags: newest, setup
        # 3 from ups_db cache:  stable, current, beta
        tags = self.eups.tags.getTagNames()
        self.assertEquals(len(tags), 5)
        for tag in "newest setup stable current beta".split():
            self.assert_(tag in tags)

        self.assertEquals(len(self.eups.preferredTags), 3)
        for tag in "stable current newest".split():
            self.assert_(tag in self.eups.preferredTags)

        # There should have been some cache files created
        flavors.append("Generic")
        for flav in flavors:
            cache = os.path.join(self.dbpath, 
                                 ProductStack.persistFilename(flav))
            self.assert_(os.path.exists(cache), 
                         "Cache file for %s not written" % flav)
        
    def testPrefTags(self):
        self.assertRaises(TagNotRecognized, 
                          self.eups.setPreferredTags, "goober gurn")
        self.eups.quiet = 1
        orig = self.eups.getPreferredTags()
        orig.sort()
        orig = " ".join(orig)
        self.eups._kindlySetPreferredTags("goober gurn")
        prefs = self.eups.getPreferredTags()
        prefs.sort()
        self.assertEquals(orig, " ".join(prefs))
        self.eups._kindlySetPreferredTags("goober stable gurn")
        self.assertEquals(" ".join(self.eups.getPreferredTags()), "stable")
        self.eups._kindlySetPreferredTags("stable beta")
        prefs = self.eups.getPreferredTags()
        prefs.sort()
        self.assertEquals(" ".join(prefs), "beta stable")

    def testFindProduct(self):

        # look for non-existent flavor
        prod = self.eups.findProduct("eigen", "2.0.0", flavor="Darwin")
        self.assert_(prod is None, "Found non-existent flavor")
        prod = self.eups.findProduct("eigen", "2.0.1", flavor="Linux")
        self.assert_(prod is None, "Found non-existent version")

        # find by name, version, flavor
        prod = self.eups.findProduct("eigen", "2.0.0", flavor="Linux")
        self.assert_(prod is not None, "Failed to find product")
        self.assertEquals(prod.name,    "eigen")
        self.assertEquals(prod.version, "2.0.0")
        self.assertEquals(prod.flavor,  "Linux")

        # look for non-existent name-version combo
        prod = self.eups.findProduct("eigen", "2.0.1")
        self.assert_(prod is None, "Found non-existent version")
                     
        # find by name, version
        prod = self.eups.findProduct("eigen", "2.0.0")
        self.assert_(prod is not None, "Failed to find product")
        self.assertEquals(prod.name,    "eigen")
        self.assertEquals(prod.version, "2.0.0")
        self.assertEquals(prod.flavor,  "Linux")

        # find by name
        prod = self.eups.findProduct("eigen")
        self.assert_(prod is not None, "Failed to find product")
        self.assertEquals(prod.name,    "eigen")
        self.assertEquals(prod.version, "2.0.0")
        self.assertEquals(prod.flavor,  "Linux")
        self.assert_("current" in prod.tags)

        # find by name, preferring tagged version
        prod = self.eups.findProduct("python")
        self.assert_(prod is not None, "Failed to find python product")
        self.assertEquals(prod.name,    "python")
        self.assertEquals(prod.version, "2.5.2")
        self.assertEquals(prod.flavor,  "Linux")
        self.assert_("current" in prod.tags)

        # find by name, preferring newest version
        tag = self.eups.tags.getTag("newest")
        prod = self.eups.findProduct("python", tag)
        self.assert_(prod is not None, "Failed to find python product")
        self.assertEquals(prod.name,    "python")
        self.assertEquals(prod.version, "2.6")
        self.assertEquals(prod.flavor,  "Linux")
        self.assertEquals(len(prod.tags), 0)

        # find by name, expression
        prod = self.eups.findProduct("python", "< 2.6")
        self.assertEquals(prod.name,    "python")
        self.assertEquals(prod.version, "2.5.2")
        self.assertEquals(prod.flavor,  "Linux")

        prod = self.eups.findProduct("python", ">= 2.6")
        self.assertEquals(prod.name,    "python")
        self.assertEquals(prod.version, "2.6")
        self.assertEquals(prod.flavor,  "Linux")

        prod = self.eups.findProduct("python", ">= 2.5.2")
        self.assertEquals(prod.name,    "python")
        self.assertEquals(prod.version, "2.5.2")
        self.assertEquals(prod.flavor,  "Linux")

        self.eups.setPreferredTags("newest")
        prod = self.eups.findProduct("python", ">= 2.5.2")
        self.assertEquals(prod.name,    "python")
        self.assertEquals(prod.version, "2.6")
        self.assertEquals(prod.flavor,  "Linux")

        prod = self.eups.findProduct("python", "== 2.5.2")
        self.assertEquals(prod.name,    "python")
        self.assertEquals(prod.version, "2.5.2")
        self.assertEquals(prod.flavor,  "Linux")

        self.assertRaises(RuntimeError, self.eups.findProduct, 
                          "python", "= 2.5.2")

        # look for a setup version
        tag = self.eups.tags.getTag("setup")
        prod = self.eups.findProduct("python", tag)
        self.assert_(prod is None, "Found unsetup product")

    def testAssignTags(self):
        prod = self.eups.getProduct("python", "2.6")
        self.assert_(prod is not None, "Failed to find python 2.6")
        if "beta" in prod.tags:
            print >> sys.stderr, "Warning: python 2.6 is already tagged beta"
        self.eups.assignTag("beta", "python", "2.6")

        self.assert_(os.path.exists(self.betachain),
                     "Failed to create beta tag file for python")
        prod = self.eups.getProduct("python", "2.6", noCache=True)
        self.assert_("beta" in prod.tags)
        prod = self.eups.getProduct("python", "2.6")
        self.assert_("beta" in prod.tags)

        # test unassign of tag to non-existent product
        self.assertRaises(ProductNotFound, 
                          self.eups.unassignTag, "beta", "goober")

        # test unassign of tag to wrong version
        q = Quiet(self.eups)
        self.eups.unassignTag("beta", "python", "2.5.2")
        del q
        self.assert_(os.path.exists(self.betachain),
                     "Incorrectly removed beta tag file for python")

        # test unassign, specifying version
        self.eups.unassignTag("beta", "python", "2.6")
        self.assert_(not os.path.exists(self.betachain),
                     "Failed ro remove beta tag file for python")

        # test unassign to any version
        self.eups.assignTag("beta", "python", "2.6")
        self.assert_(os.path.exists(self.betachain),
                     "Failed to create beta tag file for python")
        self.eups.unassignTag("beta", "python")
        self.assert_(not os.path.exists(self.betachain),
                     "Failed to remove beta tag file for python")
        prod = self.eups.findProduct("python", self.eups.tags.getTag("beta"))
        self.assert_(prod is None, "Failed to untag beta from %s" % prod)

        


    def testDeclare(self):
        pdir = os.path.join(testEupsStack, "Linux", "newprod")
        pdir10 = os.path.join(pdir, "1.0")
        pdir11 = os.path.join(pdir, "1.1")
        table = os.path.join(pdir10, "ups", "newprod.table")
#        self.eups.verbose += 1

        # test declare
        self.eups.declare("newprod", "1.0", pdir10, testEupsStack, table)
        prod = self.eups.findProduct("newprod")
        self.assert_(prod is not None, "Failed to declare product")
        self.assertEquals(prod.name,    "newprod")
        self.assertEquals(prod.version, "1.0")
        self.assertEquals(len(prod.tags), 0)
        prod = self.eups.findProduct("newprod", noCache=True)
        self.assertEquals(prod.name,    "newprod")
        self.assertEquals(prod.version, "1.0")
        self.assertEquals(len(prod.tags), 0)
        self.assert_(os.path.exists(os.path.join(self.dbpath,
                                                 "newprod", "1.0.version")))

        # test undeclare
        self.eups.undeclare("newprod", "1.0", testEupsStack)
        prod = self.eups.findProduct("newprod")
        self.assert_(prod is None, "Found undeclared product")
        prod = self.eups.findProduct("newprod", noCache=True)
        self.assert_(prod is None, "Found undeclared product")
        self.assert_(not os.path.exists(os.path.join(self.dbpath,
                                                     "newprod", "1.0.version")))

        # test declaring with tag (+ without eupsPathDir)
        self.eups.declare("newprod", "1.0", pdir10, None, table, tag="beta")
        prod = self.eups.findProduct("newprod", eupsPathDirs=testEupsStack)
        self.assert_(prod is not None, "Failed to declare product")
        self.assertEquals(len(prod.tags), 1)
        self.assertEquals(prod.tags[0], "beta")

        # test 2nd declare, w/ transfer of tag
        self.eups.declare("newprod", "1.1", pdir11, None, table, tag="beta")
        prod = self.eups.findProduct("newprod", "1.1")
        self.assert_(prod is not None, "Failed to declare product")
        self.assertEquals(prod.dir, pdir11)
        self.assertEquals(len(prod.tags), 1)
        self.assertEquals(prod.tags[0], "beta")
        prod = self.eups.findProduct("newprod", "1.0")
        self.assert_(prod is not None, "Failed to declare product")
        self.assertEquals(len(prod.tags), 0)

        # test redeclare w/change of product dir
        self.assertRaises(RuntimeError, self.eups.declare, 
                          "newprod", "1.1", pdir10, None, table, tag="beta")
        self.eups.force = True
        self.eups.declare("newprod", "1.1", pdir10, None, table, tag="beta")
        prod = self.eups.findProduct("newprod", "1.1")
        self.assert_(prod is not None, "Failed to declare product")
        self.assertEquals(prod.dir, pdir10)
        self.assertEquals(len(prod.tags), 1)
        self.assertEquals(prod.tags[0], "beta")

        # test ambiguous undeclare
        self.assertRaises(RuntimeError, self.eups.undeclare, "newprod")

        # test tagging via declare (install dir determined on fly)
        self.eups.declare("newprod", "1.0", tag="current")
        chainfile = os.path.join(self.dbpath, "newprod", "current.chain")
        self.assert_(os.path.exists(chainfile))
        prod = self.eups.findProduct("newprod", "1.0")
        self.assert_(prod is not None, "Failed to declare product")
        self.assertEquals(len(prod.tags), 1)
        self.assertEquals(prod.tags[0], "current")

        # test unassign of tag via undeclare
        self.eups.undeclare("newprod", "1.0", tag="current")
        self.assert_(not os.path.exists(chainfile))
        prod = self.eups.findProduct("newprod", "1.0")
        self.assert_(prod is not None, "Unintentionally undeclared product")
        self.assertEquals(len(prod.tags), 0)

        # test deprecated declareCurrent
        q = Quiet(self.eups)
        self.eups.declare ("newprod", "1.0", declareCurrent=True)
        self.assert_(os.path.exists(chainfile))
        prod = self.eups.findProduct("newprod", "1.0")
        self.assert_(prod is not None, "Failed to declare product")
        self.assertEquals(len(prod.tags), 1)
        self.assertEquals(prod.tags[0], "current")
        self.eups.undeclare("newprod", "1.0", undeclareCurrent=True)
        self.assert_(not os.path.exists(chainfile))
        prod = self.eups.findProduct("newprod", "1.0")
        self.assert_(prod is not None, "Unintentionally undeclared product")
        self.assertEquals(len(prod.tags), 0)

        # test deprecated declareCurrent
        self.eups.declare("newprod", "1.0", pdir10, testEupsStack, table, True)
        self.assert_(os.path.exists(chainfile))
        prod = self.eups.findProduct("newprod", "1.0")
        self.assert_(prod is not None, "Failed to declare product")
        self.assertEquals(len(prod.tags), 1)
        self.assertEquals(prod.tags[0], "current")
        self.eups.undeclare("newprod", "1.0", testEupsStack, True)
        self.assert_(not os.path.exists(chainfile))
        prod = self.eups.findProduct("newprod", "1.0")
        self.assert_(prod is not None, "Unintentionally undeclared product")
        self.assertEquals(len(prod.tags), 0)
        del q

        # test undeclare of tagged product
        self.eups.undeclare("newprod", "1.1")
        chainfile = os.path.join(self.dbpath, "newprod", "beta.chain")
        self.assert_(not os.path.exists(chainfile), 
                     "undeclared tag file still exists")
        prod = self.eups.findTaggedProduct("newprod", "beta")
        self.assert_(prod is None, "removed tag still assigned")
        prod = self.eups.findProduct("newprod")
        self.assert_(prod is not None, "all products removed")

#       needs listProducts()
        self.eups.undeclare("newprod")
        self.assert_(not os.path.exists(os.path.join(self.dbpath,"newprod")),
                     "product not fully removed")


    def testList(self):

        # basic find
        prods = self.eups.findProducts("python")
        self.assertEquals(len(prods), 2)
        self.assertEquals(prods[0].name, "python")
        self.assertEquals(prods[0].version, "2.5.2")
        self.assertEquals(prods[1].name, "python")
        self.assertEquals(prods[1].version, "2.6")
        
        prods = self.eups.findProducts("python", tags="newest")
        self.assertEquals(len(prods), 1)
        self.assertEquals(prods[0].name, "python")
        self.assertEquals(prods[0].version, "2.6")

        prods = self.eups.findProducts("py*", "2.*",)
        self.assertEquals(len(prods), 2)
        self.assertEquals(prods[0].name, "python")
        self.assertEquals(prods[0].version, "2.5.2")

        prods = self.eups.findProducts("python", "3.*",)
        self.assertEquals(len(prods), 0)

        prods = self.eups.findProducts("python", "2.5.2", tags="newest")
        self.assertEquals(len(prods), 0)

        # find all: ['cfitsio','mpich2','eigen','python:2','doxygen','tcltk']
        prods = self.eups.findProducts()
        self.assertEquals(len(prods), 7)
        
        prods = self.eups.findProducts("python", tags="setup")
        self.assertEquals(len(prods), 0)

        prods = self.eups.findProducts("python", tags="current newest".split())
        self.assertEquals(len(prods), 2)

        prods = self.eups.findProducts("doxygen")
        self.assertEquals(len(prods), 1)
        self.assertEquals(prods[0].name, "doxygen")
        self.assertEquals(prods[0].version, "1.5.7.1")
        prods = self.eups.findProducts("doxygen", 
                                       flavors="Linux Linux64".split())
        self.assertEquals(len(prods), 2)
        self.assertEquals(prods[0].name, "doxygen")
        self.assertEquals(prods[0].version, "1.5.7.1")
        self.assertEquals(prods[1].name, "doxygen")
        self.assertEquals(prods[1].version, "1.5.9")

        # test deprecated function:
        q = Quiet(self.eups)
        prods = self.eups.listProducts("python", current=True)
        self.assertEquals(len(prods), 1)
        self.assertEquals(prods[0].name, "python")
        self.assertEquals(prods[0].version, "2.5.2")
        del q

    def testSetup(self):
        # test getSetupProducts(), findSetupProduct(), findProducts(), 
        # listProducts(), findSetupVersion()
        pass


__all__ = "EupsTestCase".split()        

if __name__ == "__main__":
    unittest.main()