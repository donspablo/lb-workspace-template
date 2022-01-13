import timeit
from subprocess import run

best_time = min(
    timeit.repeat(
        lambda: run(['python3', 'utils/setup-make.py']), number=1, repeat=10))
print(best_time)
assert best_time < 0.4
