# junit-grader

This python program processes several JUnit XML files and either:

- Generate scores.csv file to show score distribution
- Grade a JUnit file according to the weights stored in the scores.csv file

As an example, assume the xml file to use is `results.xml

```console
# Generate scores
$ junit-grader.py generate results.xml

# Grade using the score weights
$ junit-grader.py grade-txt results.xml
test_library:test_one: 50/50
test_library:test_multiple: 50/50
--------------------------
100 / 100
```
