import matplotlib.pyplot as plt

data = [6, 213, 241, 260, 281, 290, 314, 321, 350, 1500]

plt.figure(figsize=(10, 6))
plt.boxplot(data, vert=False)  # vert=False for horizontal box plot
plt.xlabel('Values')
plt.title('Box Plot')
plt.grid(True, alpha=0.3)
plt.show()
