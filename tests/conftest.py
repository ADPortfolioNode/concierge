import matplotlib

# Use a non-interactive backend for matplotlib during tests to avoid
# GUI/Tkinter issues in CI and headless environments.
matplotlib.use('Agg')
