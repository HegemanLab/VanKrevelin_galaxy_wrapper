import os
import time
import extractNeededElementalData
import processElementalData
import bmrbLookup as bmrb
import argparse
import multiprocessing
from multiprocessing import Pool
from flexPlot import plotVanK
from functools import partial

parser = argparse.ArgumentParser()
parser.add_argument('--load',      '-l', nargs='?', default='',     help='Load a previously generated ratio table. Set file path. Disabled by default.')
parser.add_argument('--database',  '-d', nargs='*', default='bmrb.csv',   help='Select database(s).')
parser.add_argument('--input',     '-i', nargs='?', default='',     type=str, help='Enter full mzXML/mzML file paths. For multiple files seperate files with a space.')
parser.add_argument('--output',    '-o', action='store_true',       help='Call variable to ouput a ratio file.')
parser.add_argument('--polarity',  '-p', nargs='?', default='both', type=str, choices=['both', 'pos', 'neg'], help='Set to "pos", "neg", or "both". Default is "both". Only one plot type can be set.')
parser.add_argument('--plottype', '-pt', nargs='*', default=['scatter'], choices=['scatter', 'heatmap', '3d'], help='Set to "scatter", "heatmap", or "3d". Default is "scatter".')
parser.add_argument('--multiprocessing', '-m', action='store_true', help='Call variable to use multiprocessing. One process per core.')
args = parser.parse_args()

# read load argument
vkLoad = getattr(args, "load")

# read load argument
vkDatabase = getattr(args, "database")
#lt = []
#print(type(lt))
#for database in vkDatabase:
#  lt = bmrb.getLookupTable('databases/' + database)
lt = bmrb.getLookupTable('databases/' + vkDatabase)

# read input argument(s)
vkInputMzs = getattr(args, "input")
try:
  with open(vkInputMzs, 'r') as f:
    vkInputMzs = [tuple(map(float, i.split(','))) for i in f]
    #vkInputMzs = f.readlines()
    #vkInputMzs = f.read()
except ValueError:
  print('The %s data file could not be loaded.' % vkInputMzs)

print(type(vkInputMzs))
print(type(vkInputMzs))
print(type(vkInputMzs))
print(type(vkInputMzs))
print(type(vkInputMzs))
print(vkInputMzs)

# read output argument
vkOutput = getattr(args, "output")

# read polarity argument
vkPolarity = getattr(args, 'polarity')

# read plottype argument
vkPlotTypes = getattr(args, 'plottype')

# read multiprocessing argument
vkMultiprocessing = getattr(args, "multiprocessing")

# vk ratio dataset builder for each polarity
# dataset is list with four elements.
# input mass to charge ratios checked against database of masses with known chemical structure
# each identified mass is saved across the four elements, at a given index, of the dataset list
# the first  element represents ratio of hydrogens in identified masses structure
# the second element represents ratio of carbons                    #FLAG VERIRFY
# the third  element represents if a nitrogen is in the strcutre    #FLAG remove element, have plotter check last element != 0
# the fourth element represents ratio of nitrogens
def buildRatios(polarity, vkInputMzs):
  # get lookup table.
  # set up. elements could be changed but would need to do some editing elsewhere.
  elements = ['C', 'H', 'O', 'N']
  if polarity == 'both':
    buildRatios('pos', vkInputMzs) 
    buildRatios('neg', vkInputMzs) 
  if polarity == 'pos' or polarity == 'neg':
    index = int(polarity == 'pos') # int(True) == 1
    error = 5
    if vkMultiprocessing:
      try:
        pool = Pool()
        multiprocessMzsArgs = partial(multiprocessMzs, polarity, error)
        identified = pool.map(multiprocessMzsArgs, vkInputMzs[index])
      except Exception as e:
        print(str(e))
      finally:
        pool.close()
        pool.join()
    else:
      identified = []
      for mz in vkInputMzs[index]: # pos2 in index 1, neg in index 0
        identified.append(bmrb.getFormulaFromMass(bmrb.adjust(mz, str(polarity)), lt, tolerance=error)) # adjust mass and search in lookup table. Store result in list.
    identified = filter(lambda a: a != 'No Match', identified) # Filter out no matches
    identifiedElements = extractNeededElementalData.find_elements_values(elements_to_find=elements, compounds=identified) # Get elements from compounds
    identifiedRatios = processElementalData.process_elemental_data(identifiedElements) # Turn elements into ratios
    if vkOutput: 
      saveRatios(identifiedRatios, polarity)
    for type in vkPlotTypes:
      plotRatios(identifiedRatios, type)

def multiprocessMzs(polarity, error, inputMz): # recieves a single Mz
  return bmrb.getFormulaFromMass(bmrb.adjust(inputMz, str(polarity)), lt, tolerance=error)

# write vk ratios as csv file
def saveRatios(ratios, polarity):
  try:
    filename = 'ratios-' + time.strftime("%Y%m%d%H%M%S-") + str(polarity) + '.csv'
    with open(filename, 'w') as f: 
      for ratio in ratios:
        f.writelines(str(ratio).strip('[]') + '\n')
  except ValueError:
    print('"%s" could not be saved.' % vkLoad)

# load VK ratio csv file
# FLAG: add multiple file support
def loadRatios(vkLoad):
  try:
    # read in ratios
    with open(vkLoad, 'r') as f:
      ratios = f.readlines()
    # split ratios into proper value
    for i in range(0, len(ratios)):
      ratios[i] = ratios[i].split(', ')
    # Cast to correct type
    ratios[0] = map(lambda x: float(x), ratios[0])
    ratios[1] = map(lambda x: float(x), ratios[1])
    ratios[3] = map(lambda x: float(x), ratios[3])
    for type in vkPlotTypes:
      plotRatios(ratios, type)
  except ValueError:
    print('The %s data file could not be loaded.' % vkLoad)

def plotRatios(ratios, type):
  import pandas as pd
  import plotly
  from plotly.graph_objs import Scatter,Scatter3d,Layout,Figure
  if type == 'scatter':
    trace1 = Scatter(x=ratios[1], y=ratios[0], mode = 'markers')
    layout = Layout(title="<b>Van Krevelin Diagram</b>", 
         xaxis= dict(
           title= 'Oxygen to Carbon Ratio',
           zeroline= False,
           gridcolor='rgb(183,183,183)',
           showline=True
         ),
         yaxis=dict(
           title= 'Hydrogen to Carbon Ratio',
           gridcolor='rgb(183,183,183)',
           zeroline=False,
           showline=True
         ))
    plotly.offline.plot({"data": [trace1], "layout": layout}, filename='vk-scatter.html', image='jpeg') 
  elif type == '3d':
    trace1 = Scatter3d(x=ratios[1], y=ratios[3], z=ratios[0], mode = 'markers')
    layout = Layout(title="<b>Van Krevelin Diagram</b>", 
         scene = dict(
         xaxis= dict(
           title= 'Oxygen to Carbon Ratio',
           zeroline= False,
           gridcolor='rgb(183,183,183)',
           showline=True
         ),
         zaxis=dict(
           title= 'Hydrogen to Carbon Ratio',
           zeroline= False,
           gridcolor='rgb(183,183,183)',
           showline=True
         ),
         yaxis= dict(
           title= 'Nitrogen to Carbon Ratio',
           zeroline= False,
           gridcolor='rgb(183,183,183)',
           showline=True
         ),), 
         margin=dict(r=0, b=0, l=0, t=0))
    plotly.offline.plot({"data": [trace1], "layout": layout},filename='vk-3d.html',image='jpeg') 

if vkLoad != '':
  loadRatios(vkLoad)
else:
  buildRatios(vkPolarity, vkInputMzs)

