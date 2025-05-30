class Plant():
    plant_count = 0
    
    def __init__(self, name):
        self.name = name
        Plant.plant_count += 1
        # print('Plant created')
        # name = 'GroovyPlant'
        
    def get_name(self):
        return self.name
    
    def __str__(self):
        return f'The plant class has {Plant.plant_count} instances'


plant1 = Plant('harlod')
plant2 = Plant('maggie')
print(f'name from plant1: {plant1.get_name()}')
print(f'Plant instance: {plant1}')
print('end of file')