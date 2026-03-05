import pandas as pd
import numpy as np

data = pd.read_csv("./film_thickness_data.txt", sep=" ")
data['x'] *= 0.01
data['y'] *= 0.01
data['z'] *= 1e-9
data.to_csv("./thickness_data.txt", index=False, sep=" ")