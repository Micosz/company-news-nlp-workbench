import unittest,copy
from scipy.sparse import csr_matrix
from engine import interval,conflict,constrained,validate,pair_counts,load_dataset,experiment
class Tests(unittest.TestCase):
 def test_partial_overlap(self):
  self.assertFalse(conflict(interval('2024'),interval('10 January 2024'),0))
  self.assertTrue(conflict(interval('2023'),interval('2024'),0))
 def test_invalid_unknown(self):
  for t in ['', 'unknown','03/04/2024','2024-02-30','0000','yesterday']:self.assertIsNone(interval(t))
 def test_ranges(self):
  d=interval('13 September 2013-14 September 2013');self.assertEqual((d[1]-d[0]).days,1)
  self.assertFalse(conflict(d,interval('14 September 2013'),0))
  self.assertTrue(conflict(d,interval('16 September 2013'),0))
  self.assertFalse(conflict(d,interval('16 September 2013'),2))
 def test_unknown_bridge(self):
  p,b=constrained(csr_matrix([[1,1,0],[1,1,1],[0,1,1]]),['a','b','c'],[interval('2020'),None,interval('2024')],0)
  d=dict(p);self.assertEqual(d['a'],d['b']);self.assertNotEqual(d['a'],d['c']);self.assertEqual(len(b),1)
 def test_unknown_not_conflict(self):
  self.assertFalse(conflict(None,interval('2024'),0))
  p,b=constrained(csr_matrix([[1,1],[1,1]]),['a','b'],[None,None],0);self.assertEqual(p[0][1],p[1][1]);self.assertEqual(b,[])
 def test_pair_counts(self):
  x=pair_counts(['a','a','b'],[0,0,0]);self.assertEqual((x['tp'],x['fp'],x['fn'],x['tn']),(1,2,0,0))
 def test_duplicate_rejected(self):
  rows,_=load_dataset('ann1-dev');self.assertRaises(ValueError,validate,[rows[0],copy.deepcopy(rows[0])])
 def test_test_guard(self):self.assertRaises(ValueError,experiment,{'dataset':'ann1-test_common','phase':'development'})
 def test_row_order(self):
  a=csr_matrix([[1,1,0],[1,1,1],[0,1,1]]);ids=['a','b','c'];dates=[interval('2020'),None,interval('2024')];p,_=constrained(a,ids,dates,0)
  order=[2,0,1];q,_=constrained(a[order,:][:,order],[ids[i] for i in order],[dates[i] for i in order],0);p,q=dict(p),dict(q)
  for i in ids:
   for j in ids:self.assertEqual(p[i]==p[j],q[i]==q[j])
if __name__=='__main__':unittest.main()
