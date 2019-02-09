import copy
import logging
import testcase
import yaml

SUCCESS = '_success'

class Visitor:
  # Each visit function returns a visitor or two to the next level of the hierarchy, or
  # None if the next level of the hierarchy is not to be traversed (for example,
  # we don't want to traverse test cases in a disabled test suite).

  # To parallelize any of these traversals, we could modify the parent visitor
  # to return a flag determining whether parallelization is allowed. For
  # example, visit_suite can return true to signal that the loop over testcases
  # can be parallelized.

  def start_visit(self):
    return self.visit_environment, self.visit_environment_end

  def visit_environment(self, environment):
    return self.visit_suite, self.visit_suite_end

  def visit_suite(self, idx, suite):
    return self.visit_test_case

  def visit_testcase(self, idx, testcase):
    pass

  def visit_suite_end(self, idx, suite):
    pass

  def visit_environment_end(self, environment):
    pass

  def end_visit(self):
    return True

SUITE_ENABLED="enabled"
SUITE_SETUP="setup"
SUITE_TEARDOWN="teardown"
SUITE_NAME="name"
SUITE_SOURCE="source"
SUITE_CASES="cases"
CASE_NAME="name"
CASE_SPEC="spec"

class Manager:
  def __init__(self,environment_registry, test_suites):
    self.test_suites = test_suites

    logging.debug("envs: {}".format(environment_registry.get_names()))
    self.environments = []
    for test_env in environment_registry.list():
      self.environments.append({'test_env': test_env, 'suites': copy.deepcopy(test_suites)})


  def accept(self, visitor: Visitor):
    visit_environment, visit_environment_end = visitor.start_visit()
    if not visit_environment:
      return visitor.end_visit()

    run_passed = True
    for env in self.environments:
      visit_suite, visit_suite_end = visit_environment(env)
      if not visit_suite:
        continue


      for suite_num, suite in enumerate(env['suites']):
        visit_testcase = visit_suite(suite_num, suite)
        if not visit_testcase:
          continue

        for idx, case in enumerate(suite[SUITE_CASES]):
          visit_testcase(idx, case)

        if visit_suite_end is not None:
          visit_suite_end(suite_num, suite)

      if visit_environment_end:
        visit_environment_end(env)

    return visitor.end_visit()

def suites_from(test_files):

  # TODO(vchudnov): Append line number info to aid in error messages
  # cf: https://stackoverflow.com/a/13319530
  all_suites = []
  for filename in test_files:
    logging.info('Reading test file "{}"'.format(filename))
    with open(filename, 'r') as stream:
      spec = yaml.load(stream)
      these_suites = spec["test"]["suites"]
      for suite in these_suites:
        suite["source"] = filename
      all_suites.extend(these_suites)
  return all_suites
