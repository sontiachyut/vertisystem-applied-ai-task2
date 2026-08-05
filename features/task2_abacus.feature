Feature: Distributed abacus sum microservice
  The system demonstrates a FastAPI microservice with a shared running sum
  that remains correct across multiple service nodes.

  Background:
    Given an abacus service backed by shared authoritative storage
    And the service is implemented with FastAPI on Python 3.12+

  Scenario: Initial sum is zero
    When a client requests GET /abacus/sum
    Then the response status should be 200
    And the response body should be {"sum": 0}

  Scenario: Posting a number increments the running sum
    When a client posts {"number": 7} to POST /abacus/number
    Then the response status should be 200
    And the response body should be {"sum": 7}
    When a client requests GET /abacus/sum
    Then the response body should be {"sum": 7}

  Scenario: Multiple posts accumulate correctly
    Given the current running sum is 0
    When a client posts {"number": 4} to POST /abacus/number
    And a client posts {"number": 9} to POST /abacus/number
    And a client posts {"number": -3} to POST /abacus/number
    Then a subsequent GET /abacus/sum should return {"sum": 10}

  Scenario: Delete resets the running sum
    Given the current running sum is 19
    When a client sends DELETE /abacus/sum
    Then the response status should be 200
    And the response body should be {"sum": 0}
    And a subsequent GET /abacus/sum should return {"sum": 0}

  Scenario: Invalid POST payload is rejected without mutating state
    Given the current running sum is 11
    When a client posts {"number": "abc"} to POST /abacus/number
    Then the response status should be 422
    And a subsequent GET /abacus/sum should return {"sum": 11}

  Scenario: Boolean payload is rejected without mutating state
    Given the current running sum is 11
    When a client posts {"number": true} to POST /abacus/number
    Then the response status should be 422
    And a subsequent GET /abacus/sum should return {"sum": 11}

  Scenario: Overflowing writes are rejected without mutating state
    Given the current running sum is 9223372036854775807
    When a client posts {"number": 1} to POST /abacus/number
    Then the response status should be 409
    And a subsequent GET /abacus/sum should return {"sum": 9223372036854775807}

  Scenario: Two service nodes share the same committed sum
    Given Node A and Node B are connected to the same authoritative store
    When a client posts {"number": 5} to Node A at POST /abacus/number
    Then a client requesting GET /abacus/sum from Node B should receive {"sum": 5}

  Scenario: Reset on one node is visible on another node
    Given Node A and Node B are connected to the same authoritative store
    And the current running sum is 14
    When a client sends DELETE /abacus/sum to Node B
    Then a client requesting GET /abacus/sum from Node A should receive {"sum": 0}

  Scenario: Concurrent posts do not lose updates
    Given the current running sum is 0
    When 100 concurrent clients each post {"number": 1} across the available nodes
    Then the final GET /abacus/sum should return {"sum": 100}

  Scenario: Concurrent reset and add operations serialize cleanly
    Given the current running sum is 10
    When one client posts {"number": 5} while another client sends DELETE /abacus/sum
    Then the final sum should match a valid committed operation order
    And the final sum should be either 0 or 5
