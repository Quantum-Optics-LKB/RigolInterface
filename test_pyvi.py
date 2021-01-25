import visa

rm = visa.ResourceManager('@py')

instruments = rm.list_resources()

print(instruments)
