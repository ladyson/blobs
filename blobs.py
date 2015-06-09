### blobs code, v0.7
### contributors: jgiuffrida@uchicago.edu
### 6/9/15

import pysal as ps
import numpy as np
import pandas as pd
from pysal.contrib.viz import mapping as maps
import matplotlib.pyplot as plt
import time
import cmd
import datetime
from mpl_toolkits.mplot3d import Axes3D
from sklearn.cluster import KMeans


# histogram helper function
def hist(data, title='Histogram of Values', bins=20, range=None):
    """Create a nice-looking histogram.

    Parameters
    ----------

    data            : array
                      n*1 vector of observations on variable of interest

    title           : string
                      title for the chart

    bins            : int
                      number of bins in which to group observations

    Attributes
    ----------

    none

    Examples
    --------

    >>> import numpy as np
    >>> x = np.random.rand(100,1)
    >>> hist(x, title='Random Uniform Distribution', bins=8)

    """

    if not range:
        range = (data.min(), data.max())

    hist, bins = np.histogram(data, bins=bins, range=range)
    width = 0.7 * (bins[1] - bins[0])
    center = (bins[:-1] + bins[1:]) / 2
    plt.bar(center, hist, align='center', width=width)
    plt.title(title)
    plt.show()


# helper function to determine how to color choropleth
def sort_regions(self, method='objective'):
    sr = np.zeros([self.k,2])
    for region in range(0,self.k):
        sr[region][0] = region
        selectionIDs = [self.w.id_order.index(i) for i in self.regions[region]]
        m = self.z[selectionIDs, :]
        if method == 'objective':
            var = m.var(axis=0)
            sr[region][1] = sum(np.transpose(var)) * len(self.regions[region])
        elif method == 'mean':
            sr[region][1] = m.mean()  # simple mean of all variables
    srdf = pd.DataFrame(sr)
    srdf = srdf.sort(columns=1)
    self.sorted_regions = dict()
    for i in range(0,self.k):
        self.sorted_regions[int(srdf[i:i+1][0])] = i

# extend blobs with a few more variables to remember what we did
ps.Maxp.sort_regions = sort_regions
ps.Maxp.floor_var = None
ps.Maxp.vars_to_use = None

# main blobs method
class Blobs:

    """Create a max-p regions solution for a given shapefile and associated 
    dataset. Builds on pysal.Maxp with improvements to the user interface, 
    flexibility, and mapping. 

    Original solution from "The Max-p-Regions Problem," Duque, Anselin, and Rey, 
    JRS, October 2010, available at http://geography.sdsu.edu/Research/
    Projects/IPC/publication/MaxP_authored.pdf

    Parameters
    ----------
    df          : pandas DataFrame
                  columns should be the floor variable and any columns  
    v           : array
                  array of variables on which to create blobs (for all 
                    variables, use ['all'])

    min_pop     : int
                  minimum population in each blob

    iterations  : int
                  number of blobs solutions to create (will return best): 10 by 
                    default

    method      : {'equal votes', 'default', 'weighted'}
                  equal votes' by default, can change to 'weighted'

    weights     : array
                  if method='weighted', add weights for variables as an array

    initial     : int
                  number of times to revise each solution (10 by default)

    plot        : boolean
                  will plot the best solution (True by default)

    savedata    : boolean
                  will save a CSV of the blobs data to the root folder (False 
                    by default)

    plot_values : boolean
                  will color-code the plot by the mean of the underlying 
                    variables. only makes sense with one variable. default 
                    False (plots by ID of the blob)
    
    Sample usage
    ------------

    >>> blobs(['all_calls_per1000'], min_pop=10000, plot_values=True)

    """

    def __init__(self, df, w, shp_link):
        self.d = df
        self.w = w
        self.shp_link = shp_link
        self.r = None
        self.regions = None
        self.blobs_data = None

    def _get_floor_var(self):
        return self.d['pop']

    def build_blobs(self, floor_var, floor, vars_to_use=[], iterations=10, 
    method='equal votes', weights=[], initial=10, plot=True, savedata=False, 
    plot_values=False, verbose=False):
        """ Method to create a blobs solution.
            floor_var is either the name of the variable, or "areas" to set the floor
            to a certain number of areas
        """
        solutions = []
        top_scores = []
        times = []
        num_blobs = []
        current_time = []
        iteration = []
        best_score = -1
        best_solution = None
        if floor_var == 'areas':
            floor_var_array = np.ones((self.d.shape[0], 1))
        else:
            floor_var_array = self.d[floor_var]
        if vars_to_use == []:
            vars_to_use = self.d.columns
        # if len(vars_to_use) > 1:
        #    vars_to_use = vars_to_use[vars_to_use != floor_var]
        blob_vars = np.array(self.d.loc[:, vars_to_use], np.float64)
        
        if len(vars_to_use) == 1:
            # add shape to the array
            blob_vars.shape = (blob_vars.shape[0], 1)
        print('\n### CREATING BLOBS FROM ' + str(len(vars_to_use)) + 
            ' VARIABLES ###\n    PARAMETERS:\n     # Minimum ' + floor_var + ' in each blob: ' + 
            str(int(floor)) + '\n     # Iterations: ' + str(iterations) +
            '\n     # Method: ' + method + '\n     # Plot blobs: ' + str(plot) + 
            '\n     # Save blobs data: ' + str(savedata) + '\n')

        for i in range(0,iterations):
            start = time.time()
            r=ps.Maxp(self.w, blob_vars, 
                floor=floor, floor_variable=floor_var_array, initial=initial, verbose=verbose)
            end = time.time()
            times.append(end - start)
            current_time.append(end)
            current_score = r.objective_function()
            solutions.append(current_score)
            num_blobs.append(r.k)
            if (best_score == -1 or current_score < best_score):
                best_score = current_score
                best_solution = r
            top_scores.append(best_score)
            iteration.append(i)
            msg = '\n# ITERATION '+str(i+1)+'                 \n  Score: ' + \
                str(round(current_score,2)) + '\n  Created '+str(r.k)+' blobs (' + \
                str(int(self.d.shape[0]/r.k)) + ' tracts per blob)\n  Best solution so far: ' + \
                str(round(best_score,2))
            msg += '\n  Time taken: '+str(round(end-start,1))+' seconds ('+ \
                str(int(np.mean(times)*(iterations-i-1)))+' seconds remaining)\n'
            print msg
        
        r = best_solution
        r.floor_var = floor_var
        r.vars_to_use = vars_to_use
        print('\r# BEST SOLUTION:                      \n  Score: '+
            str(round(r.objective_function(),2)) + 
            '\n  '+str(r.k)+' blobs ('+str(int(self.d.shape[0]/r.k))+
            ' tracts per blob)')
        self.r = r
        # prep for plotting
        ids=np.array(self.d['tractce10']).astype(str)
        if plot_values:
            self.r.sort_regions(method='mean')  # sort regions by intensity of the variable
        regions=np.empty(self.d.shape[0])
        for j in range(0,self.d.shape[0]):
            reg=r.area2region[ids[j]]
            regions[j]=reg
        self.regions = regions
        if plot:
            self.plot()
        self.build_data_structure(savedata)

    # helper function to assign weights to variables
    def _format_blobs(self, data, option='equal votes', weights=None):
        if option == 'default':
            # use max p as originally designed
            # variables will be implicitly weighted in proportion to their means
            return data
        elif option == 'equal votes':
            # give equal weight to all variables by standardizing them
            x = np.zeros(data.shape)
            for v in range(data.shape[1]):
                x[:,v] = (data[:,v] - np.mean(data[:,v])) / np.std(data[:,v])
            return x
        elif option == 'weighted':
            # assign explicit weights to standardized variables
            x = np.zeros(data.shape)
            for v in range(data.shape[1]):
                x[:,v] = ((data[:,v] - np.mean(data[:,v])) / \
                    np.std(data[:,v])) * np.sqrt(weights[v])
            return x

    def plot(self):
        # show blobs we created
        print('  Plotting...'),
        maps.plot_choropleth(self.shp_link, self.regions, type='quantiles',
            title='Chicago blobs from census tracts\n(min ' + 
                str(int(self.r.floor)) +' population per blob, ' + 
                str(self.r.p)+' blobs)', k=self.r.p, figsize=(6,9))
        print('\r             \n')

    def build_data_structure(self, savedata=True):
        #build data structure
        sr = np.zeros([self.r.k, len(self.r.vars_to_use)*2+4])
        for region in range(0,self.r.k):
            # blob ID
            sr[region][0] = region
            selectionIDs = [self.r.w.id_order.index(i) for i in self.r.regions[region]]
            m = self.r.z[selectionIDs, :]
            # objective function
            var = m.var(axis=0)
            sr[region][1] = sum(np.transpose(var)) * len(self.r.regions[region])
            # blob size (number of places in blob)
            sr[region][2] = len(self.r.regions[region])
            # blob population
            sr[region][3] = self.d.loc[selectionIDs, self.r.floor_var].sum()
            # variable means and standard deviations
            for j in range(0,len(self.r.vars_to_use)):
                sr[region][4+j*2] = m[:,j].mean()
                sr[region][5+j*2] = m[:,j].std()
        srdf = pd.DataFrame(sr)
        cols = ['Blob', 'Score', 'Size', self.r.floor_var]
        for j in range(0, len(self.r.vars_to_use)):
            cols.append(self.r.vars_to_use[j]+'_mean')
            cols.append(self.r.vars_to_use[j]+'_stdev')
        srdf.columns = cols
        if savedata:
            srdf.to_csv('Blobs data ' + datetime.datetime.now().strftime('%Y%m%d %H%M') + \
                '.csv', index=False)
        self.blobs_data = srdf

    # helper function to retrieve original, non-standardized data about a blob
    def retrieve_raw_data(self):
        pass  # todo




# command line processor
class CmdBlobs(cmd.Cmd):
    """Command line interface for blobs"""

    variables = ['tract', 'pop', 'ca', 'vehicles', 'alley_lights', 'garbage',
        'graffiti', 'potholes', 'rodents', 'sanitation', 'street_lights_one',
        'street_lights_all', 'tree_debris', 'tree_trims', 'buildings',
        'vehicles_per1000', 'alley_lights_per1000', 'garbage_per1000',
        'graffiti_per1000', 'potholes_per1000', 'rodents_per1000',
        'sanitation_per1000', 'street_lights_one_per1000',
        'street_lights_all_per1000', 'tree_debris_per1000',
        'tree_trims_per1000', 'buildings_per1000', 'all_calls',
        'all_calls_per1000', 'tractce10', 'commarea', 'order']

    picked = []
    floor_var = ''
    floor_size = 0
    iterations = 10
    method = 'equal votes'
    weights = []
    plot = True
    savedata = True
    r = None

    step = 1

    def clear_vars(self):
        self.picked = []
        self.floor_var = ''
        self.floor_size = 0
        self.iterations = 10
        self.method = 'equal votes'
        self.weights = []
        self.plot = True
        self.savedata = True
        self.r = None
        self.step = 1
    
    def do_select(self, name):
        "Step 1: select a variable"
        if name and name in self.variables:
            response = '\n  Added %s.\n  Add more variables or enter command \'next\'.\n' % name
            self.picked.append(name)
        elif name:
            response = '\nError: could not find variable %s\n' % name
        else:
            response = '\nError: please give a variable\n'
        print response
    
    def complete_select(self, text, line, begidx, endidx):
        "Autocomplete variable selection"
        if not text:
            completions = [ f
                            for f in self.variables
                            if f not in self.picked
                            ]
        else:
            completions = [ f
                            for f in self.variables
                            if (f.startswith(text)
                            and f not in self.picked)
                            ]
        return completions
    
    def do_floor(self, name):
        "Step 2 part 1: Select floor variable"
        if name and name in self.variables:
            response = '\n  %s set as floor variable.\n' % name
            self.floor_var = name
            response += '\n  Now, please enter command '+\
                '\'size\' followed by the minimum floor size\n  you would like to set. '+\
                'To help, we\'ve provided you with a histogram \n  of %s values.\n' % name
            print response
            hist(self.d[name], title='Histogram of '+name)
        elif name:
            response = '\nError: could not find variable %s\n' % name
            print response
        else:
            response = '\nError: please give a variable\n'
            print response

    def complete_floor(self, text, line, begidx, endidx):
        "Autocomplete floor variable selection"
        if not text:
            completions = self.variables[:]
        else:
            completions = [ f
                            for f in self.variables
                            if f.startswith(text)
                            ]
        return completions

    def do_size(self, size):
        "Step 2 part 2: Set size of floor"
        if float(size) > 0:
            response = '\n  %s set as minimum floor\n' % str(size)
            self.floor_size = float(size)
            print response
            self.do_next('')
        elif size:
            response = '\nError: size should not be 0\n'
            print response
        else:
            response = '\nPlease set the size\n'
            print response

    def do_iterations(self, num):
        "Set number of iterations"
        if int(num) > 0:
            response = '\n  %s set as number of iterations\n' % str(int(num))
            self.iterations = int(num)
        else:
            response = '\nError: must set number of iterations\n'
        print response

    def do_method(self, line):
        "Set method"
        if line in ['equal votes', 'weighted', 'default']:
            response = '\n  %s set as method\n' % line
            self.method = line
        else:
            response = '\nError: must set method equal to \'equal votes\', '+\
                '\'weighted\', or \'default\'\n'
        print response

    def do_weights(self, line):
        "Set weights"
        # this method has not been fleshed out
        pass

    def do_plot(self, line):
        "Set whether to plot"
        if line in ['true', 'True', 't', 'T', 'y', 'Y']:
            response = '\n  The blobs map will be shown\n'
            self.plot = True
        elif line in ['false', 'False', 'f', 'F', 'n', 'N']:
            response = '\n  The blobs map will NOT be shown\n'
            self.plot = False
        else:
            response = '\nError: must set plot to \'True\' or \'False\'\n'
        print response

    def do_savedata(self, line):
        "Set whether to save data"
        if line in ['true', 'True', 't', 'T', 'y', 'Y']:
            response = '\n  The blobs data will be saved to the root folder\n'
            self.savedata = True
        elif line in ['false', 'False', 'f', 'F', 'n', 'N']:
            response = '\n  The blobs data will NOT be saved\n'
            self.savedata = False
        else:
            response = '\nError: must set savedata to \'True\' or \'False\'\n'
        print response


    def do_next(self, line):
        self.step += 1
        if self.step == 2:
                self.variables = variables
                print '\n## Step 2: Set Blob Size'
                print('  Enter command \'floor\' followed by the variable you want '+
                    'to use\n  as the \'floor\' variable. Use tab key to autocomplete.\n')
        if self.step == 3:
            response = '\n## Step 3: Run Blobs\n  Ready to run blobs. Parameters:'+\
                '\n  Variables: '
            for v in self.picked:
                response += '\n    %s' % v
            response += '\n  Floor Variable: %s' % self.floor_var
            response += '\n  Floor Size: %s' % str(self.floor_size)
            response += '\n  Iterations: %s' % str(self.iterations)
            response += '\n  Method: %s' % self.method
            response += '\n  Weights: %s' % str(self.weights)
            response += '\n  Plot: %s' % str(self.plot)
            response += '\n  Save Data: %s' % str(self.savedata)
            response += '\n\n  To run blobs using these parameters, enter command '+\
                '\'run\'.\n  To change any of the parameters, enter one of the following '+\
                '\n  commands, followed by the desired value:'+\
                '\n    iterations, method, weights, plot, savedata'+\
                '\n  To exit, enter command \'exit\'.\n'
            print response
        if self.step == 4:
            response = '\n## Step 4: Cluster Blobs\n  Ready to assign blobs to clusters. '+\
                'Please enter command \'cluster\' \n  followed by the average number of blobs '+\
                'you want in each cluster.\n  A good value might be the number of blobs '+\
                'divided by 10 or 20. Or\n  enter command \'exit\' to exit.\n'
            print response
        if self.step == 5:
            self.do_exit('')
    
    def do_exit(self, line):
        return True

    def do_run(self, line):
        self.r = blobs(self.picked, self.floor_size, floor_var=self.floor_var, 
            iterations=self.iterations, method=self.method, weights=self.weights,
            plot=self.plot, savedata=self.savedata)
        self.do_next('')

    def do_cluster(self, clusters):
        if int(clusters) > 0:
            Cluster_blobs(self.r['data'], blobs_per_cluster=int(clusters))
            self.do_next('')
        else:
            print('Error: must set number of blobs per cluster')
   

def interface():
    """
    Example usage:
    --------------

    >>> interface()
    (Cmd) select sanitation_per1000
    (Cmd) select garbage_per1000
    (Cmd) select rodents_per1000
    (Cmd) next
    (Cmd) floor pop
    (Cmd) size 20000
    (Cmd) savedata False
    (Cmd) iterations 5
    (Cmd) run
    (Cmd) cluster 15
    (Cmd) cluster 8
    (Cmd) cluster 20
    (Cmd) exit

    """

    print '\nThis is a command line interface for Blobs.'
    print '\n## Step 1: Select Variables'
    print('  Enter command \'select\' followed by a variable you want. Use tab key '+
        '\n  to see options or autocomplete. When finished, enter command \'next\'.\n'+
        '  At any time, you can enter command \'exit\' to exit.\n')
    newUI = CmdBlobs()
    newUI.clear_vars()  # clear any variables from a previous usage
    newUI.cmdloop()


# cluster the blobs data (k-means)
class Cluster_blobs:
    """Use k-means to cluster blobs along the explanatory variables.

    Parameters
    ----------

    w               : pandas DataFrame
                      should be a blobs data structure, accessible by calling 
                        the "data" attribute of a Blobs() object

    variables       : array
                      an array of variable names to use for clustering; by 
                        default, all variables ending in "_mean" will be used

    n_clusters      : int
                      (optional) number of clusters to form

    blobs_per_      : int
      cluster         (optional) average number of blobs per cluster. if both
                        n_clusters and blobs_per_cluster have values, the 
                        former will be ignored

    Attributes
    ----------

    assignments     : numpy array
                      an n*1 array of cluster labels, in order

    centers         : pandas DataFrame
                      the coordinates for the cluster centers, in order

    inertia         : float
                      the "inertia" for the final solution; lower is better

    Sample usage
    ------------

    >>> solution = Blobs(dataset, min_pop=10000)
    >>> cl = Cluster_blobs(solution.data, blobs_per_cluster=10)
    >>> print(cl.centers)

    """

    def __init__(self, v, variables=[], n_clusters=0, blobs_per_cluster=0):
        """Initialize, run k-means, and plot."""
        # build list of variables on which to cluster (if not provided)
        if variables == []:
            self.cluster_vars = []
            for c in v.columns:
                if c.find('_mean') > 0:
                    self.cluster_vars.append(c)
        else:
            self.cluster_vars = variables

        self.x = np.array(v[self.cluster_vars])
        self.n_clusters = n_clusters
        self.blobs_per_cluster = blobs_per_cluster
        self._set_clusters()

        self.assignments = None
        self.centers = None
        self.inertia = -1
        self.kmeans()
        self.plot()

    def _set_clusters(self):
        """Recalculate number of clusters."""
        # set n_clusters
        if self.n_clusters == 0 and self.blobs_per_cluster == 0:
            self.blobs_per_cluster = 10  # totally arbitrary
            self.n_clusters = int(np.round(self.x.shape[0] / 
                self.blobs_per_cluster))
        elif self.blobs_per_cluster:
            self.n_clusters = int(np.round(self.x.shape[0] / self.blobs_per_cluster))
        elif self.n_clusters:
            self.blobs_per_cluster = int(np.round(self.x.shape[0] / self.n_clusters))

    def kmeans(self):
        """Run k-means with current settings."""
        # run k-means with all available CPU cores
        self.est = KMeans(n_clusters=self.n_clusters, n_jobs=-1) 
        # the preceding can throw an error in multiprocessing.py in pycharm; change to n_jobs=1 to fix
        self.est.fit(self.x)
        # save a lot of data to work with, save, etc.
        self.assignments = self.est.labels_ 
        self.centers = pd.DataFrame(self.est.cluster_centers_, columns=self.cluster_vars)
        self.inertia = self.est.inertia_


    def plot(self, variables=[]):
        """Plot the most recent k-means solution.

        Parameters
        ----------

        variables   : array
                      list of variables to plot (by default, uses variables 
                        used in kmeans). if only two are provided, will plot in 2D.

        """
        fig = plt.figure(figsize=(10, 9))
        plt.clf()

        if len(variables) == 0:
            vars_to_plot = self.cluster_vars
        else:
            vars_to_plot = variables

        pos = {}

        
        if len(vars_to_plot) == 1:
            print('No graph shown because only one variable was used')
            return True
        elif len(vars_to_plot) == 2:
            ax = fig.add_subplot(111)
        else:
            # will automatically plot in 3D if 3+ variables
            ax = Axes3D(fig, rect=[0, 0, .95, 1], elev=30, azim=134)


        plt.cla()
        labels = self.est.labels_

        # click event to print data about each point on user interaction
        def onpick(event):
            ind = event.ind
            for i in ind:
                type = event.artist.get_label()
                msg = ''
                if type == 'Blobs':
                    msg = 'Blob ' + str(i)
                    for c in range(self.x.shape[1]):
                        msg += '\n  ' + self.cluster_vars[c][:self.cluster_vars[c].find('_mean')]+\
                                ': ' + str(round(np.take(self.x[:,c], i), 2))
                    msg += '\n  (All values are z-scores)'
                    neighbors = np.where(self.est.labels_ == self.est.labels_[i])[0]
                    if len(neighbors) > 1:
                        msg += '\n  Other blobs in cluster: ' + \
                                ', '.join([k for k in neighbors.astype('str') if not k==str(i)]) + \
                                '\n'
                elif type == 'Clusters':
                    msg = 'Cluster ' + str(i)
                    msg += '\n  Center of cluster (all values in z-scores):'
                    for c in range(self.est.cluster_centers_.shape[1]):
                        msg += '\n  ' + self.cluster_vars[c][:self.cluster_vars[c].find('_mean')]+\
                                ': ' + str(round(np.take(self.est.cluster_centers_[:,c], i), 2))
                    inhabitants = np.where(self.est.labels_ == i)[0]
                    msg += '\n  Blobs in cluster: ' + \
                            ', '.join([k for k in inhabitants.astype('str') if not k==str(i)])+'\n'
                print msg

        # prepare scatterplots and axes
        if len(vars_to_plot) == 2:
            ax.scatter(x[:, self.cluster_vars.index(vars_to_plot[0])], 
                x[:, self.cluster_vars.index(vars_to_plot[1])], s=30, 
                c=labels.astype(np.float),label="Blobs",picker=True)
            ax.scatter(self.est.cluster_centers_[:,self.cluster_vars.index(vars_to_plot[0])], 
                self.est.cluster_centers_[:,self.cluster_vars.index(vars_to_plot[1])], s=40, 
                marker='*', c=range(self.est.n_clusters), label="Clusters", picker=True)
            ax.xaxis.set_ticklabels(ax.xaxis.get_ticklocs())
            ax.yaxis.set_ticklabels(ax.yaxis.get_ticklocs())
            ax.set_xlabel(vars_to_plot[0])
            ax.set_ylabel(vars_to_plot[1])
        elif len(vars_to_plot) > 2:
            ax.scatter(self.x[:, self.cluster_vars.index(vars_to_plot[0])], 
                self.x[:, self.cluster_vars.index(vars_to_plot[1])], 
                self.x[:, self.cluster_vars.index(vars_to_plot[2])], s=30, 
                c=labels.astype(np.float), label="Blobs", picker=True)
            ax.scatter(self.est.cluster_centers_[:,self.cluster_vars.index(vars_to_plot[0])], 
                self.est.cluster_centers_[:,self.cluster_vars.index(vars_to_plot[1])], 
                self.est.cluster_centers_[:,self.cluster_vars.index(vars_to_plot[2])], 
                s=40, marker='*', c=range(self.est.n_clusters), label="Clusters", picker=True)
            ax.w_xaxis.set_ticklabels(ax.w_xaxis.get_ticklocs())
            ax.w_yaxis.set_ticklabels(ax.w_yaxis.get_ticklocs())
            ax.w_zaxis.set_ticklabels(ax.w_zaxis.get_ticklocs())
            ax.set_xlabel(vars_to_plot[0])
            ax.set_ylabel(vars_to_plot[1])
            ax.set_zlabel(vars_to_plot[2])
        ax.set_axisbelow(True)
        fig.canvas.mpl_connect('pick_event', onpick)

        plt.title(str(self.x.shape[0]) + ' Blobs in ' + str(self.est.n_clusters) + 
            ' Clusters (Based on ' + str(len(vars_to_plot)) + 
                ' variables)\nClick on values for more information')
        plt.show()


    def set_n_clusters(self, n_clusters):
        """Set the desired number of clusters."""
        # reset number of clusters
        if int(n_clusters) > 0:
            self.n_clusters = n_clusters
            self.blobs_per_cluster = 0
            self._set_clusters()
        else:
            print("Error: please provide n_clusters as an int")

    def set_blobs_per_cluster(self, blobs_per_cluster):
        """Set the desired number of blobs per cluster."""
        # reset number of blobs per cluster
        if int(blobs_per_cluster) > 0:
            self.blobs_per_cluster = blobs_per_cluster
            self.n_clusters = 0
            self._set_clusters()
        else:
            print("Error: please provide blobs_per_cluster as an int")


