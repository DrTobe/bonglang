class FlatList:
	def __init__(self, elements):
		self.elements = elements
	# Flattened append (no FlatList inside a FlatList)
	def append(self, element): # element : typing.Union[ElementType, FlatList]
		if isinstance(element, FlatList):
			for contained_element in element.elements:
				self.elements.append(contained_element)
		else:
			self.elements.append(element)
	# The next two methods for index-access and length
	def __len__(self):
		return len(self.elements)
	def __getitem__(self, index):
		return self.elements[index]
	# The next two methods make this class iterable
	def __iter__(self):
		self.iterationCounter = -1
		return self
	def __next__(self):
		self.iterationCounter += 1
		if self.iterationCounter < len(self.elements):
			return self.elements[self.iterationCounter]
		raise StopIteration
	def __str__(self):
		return "FlatList [" + ", ".join(map(str,self.elements)) + "]"
