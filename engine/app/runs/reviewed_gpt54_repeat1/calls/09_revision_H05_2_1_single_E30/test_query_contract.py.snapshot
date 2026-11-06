import unittest
from agent_common import validate_json
from research_workflow import QP
class QueryContract(unittest.TestCase):
 def test_lexical_terms(self):
  query=dict(id='Q2_method',question_id='Q2',channel='method',question='State',term_groups=[['insitu','spectroscopy']])
  validate_json(dict(queries=[query]),QP)
  query['term_groups']=[['in situ']]
  with self.assertRaises(Exception):validate_json(dict(queries=[query]),QP)
