# The agent relocates to the nearest popular FBO
#
# Step 1: Bootstraps the delivery fleet. Starts with zero agents and
# progressively creates them to meet the requested order volume. Outputs
# shift-wise fleet sizes required across the day.
#
# Code accompanying:
#   Sinha, D., & Pandit, D. (2021). A simulation-based study to determine
#   the negative externalities of hyper-local food delivery. Transportation
#   Research Part D, 100, 103071.

import math
import random
import statistics
import os
import csv

import matplotlib.pyplot as plt
import numpy
import pandas as pd

import common
from common import (
    N_FBOS,
    N_CUSTOMER_POINTS,
    MOTORBIKE_KMH,
    BICYCLE_KMH,
    CUSTOMER_PAY_PER_ORDER,
    WAIT_TIME_PAY_PER_MIN,
)

# --- Load shared data (once) ---
point_fboDF, fbo_fboDF, file4 = common.load_distance_matrices()
_distributions = common.load_distributions()
FBO_POPULARITY_PROB = _distributions["fbo_popularity"].values
ORDER_HOUR_SUPPORT = _distributions["order_hour"].index.to_numpy()
ORDER_HOUR_PROB = _distributions["order_hour"].values
WAIT_TIME_SUPPORT = _distributions["wait_time_minutes"].index.to_numpy()
WAIT_TIME_PROB = _distributions["wait_time_minutes"].values
WORK_HOURS_SUPPORT = _distributions["work_hours"].index.to_numpy()
WORK_HOURS_PROB = _distributions["work_hours"].values


class Agent:
    """Creating an Agent Class that takes the list of FBOs as parameters.
        Each Agent object created is randomly assigned a FBO location as the initial location.
        An id_counter is created to keep track of the number of agents instantiated.
        The time stamp keeps note of the time till the agent remains inactive.
        """
    id_counter = 0
    def __init__(self, fbo_FID, tim, vehicle, cloudkitchen, workhourlimit):
        self.vehicle = vehicle  # 0 is bike, 1 is cycle, 0 set as default
        if vehicle == 0:
            self.velocity = MOTORBIKE_KMH  # motorbike velocity
        else:
            self.velocity = BICYCLE_KMH  # cycle velocity
        if cloudkitchen == None:
            self.location = numpy.random.choice(numpy.arange(0, N_FBOS), p=FBO_POPULARITY_PROB)
            # the agent is not spawned at the eatery location to reflect a more realistic situation
        else:
            self.location = cloudkitchen
        self.id = Agent.id_counter
        Agent.id_counter += 1
        self.time = 0
        self.first_mile = []
        self.last_mile = []
        self.dead_mile = []
        self.total_waiting_time = 0
        self.delivery_time = []
        self.distTimeGraph = []
        self.orders_delivered = 0
        self.current_earning = 0
        self.total_riding_time = 0
        self.total_working_time = 0
        self.spawn_time = tim
        self.work_hours = 0
        w = numpy.random.choice(WORK_HOURS_SUPPORT, p=WORK_HOURS_PROB)
        # if the workhour exceeds the workhourlimit, it is set to the maximum
        if workhourlimit != None:
            print("Setting the workhour limit to 12, which is currently", w)
            if w >= workhourlimit:
                w = workhourlimit - 1
        self.work_hours = w + (random.randrange(0, 100) / 100)
        print("The new workhour of the agent is", self.work_hours)


    def set_mile(self, fm, sm, tm, rtym, act_wt_tym):
        """Once an order is assigned
            The total 1st mile, 2nd mile and 3rd mile is updated.
                """
        self.first_mile.append(fm)
        self.last_mile.append(sm)
        self.dead_mile.append(tm)
        print("The agent's riding time till now was", self.total_riding_time)
        self.total_riding_time += rtym
        print("The agent's active time till now is", self.total_riding_time)
        self.total_waiting_time += act_wt_tym

    def set_time(self, time):
        """Once an order is assigned, the total time for delivery is
            added to the "time till agent is inactive".
                """
        self.time = time

    def set_location(self, location):
        """Once an order is assigned, the location is updated as the location of the FBO
            at the end of the third mile.
                """
        self.location = location

    def set_orders_delivered(self, length):
        """Once an order is assigned, the number of orders delivered by the agent is updated.
                        """
        self.orders_delivered += length

    def update_wage(self, earning):
        self.current_earning = self.current_earning + earning

    def get_value(self):
        """The method returns the agent characteristics at any point in time.
                        """
        self.agent = [self.id, self.location, self.time,
                      self.first_mile, self.last_mile,
                      self.dead_mile, self.orders_delivered]
        return self.agent

class Model:
    """The main model class

        """
    def __init__(self, order_num, cloudkitchen, cyclewage, bicycleKMlimit, sar, workhourLimit):
        self.fbo_FID = list(range(N_FBOS))
        self.order_num = order_num
        self.agent_dict = {}
        self.order_dict = {}
        self.special_delivery_time = []
        self.delivery_time = []
        #self.sl = 0
        self.cloudkitchen = cloudkitchen
        self.orders_fulfilled_bike = 0
        self.orders_fulfilled_bicycle = 0
        self.orderBatches = []
        self.cycle_wage = cyclewage
        self.bicycleKMlimit = bicycleKMlimit
        self.service_area_radius = sar
        self.workhour_limit = workhourLimit

    def modelRun(self,relocateflag, threshold, timeband, delivery_time_limit, max_batching_limit):
        self.order_generator()
        #self.order_generator_dynamic_serviceArea()
        self.popularity_mapper()
        print("Generating orders: self.order_dict", self.order_dict)
        print("Popularity list", self.popularity_map)

        orderbundl_dict = {}
        counter = 0
        tymSlab = self.order_dict[0][1] + timeband
        # print("First tymSlab", tymSlab)
        listy = []
        i = 0
        while i < len(self.order_dict):
            # print("j[1]", self.order_dict[i][1])
            # print("tymSlab", tymSlab)
            if self.order_dict[i][1] <= tymSlab:
                # print("If is true")
                listy.append(i)
                orderbundl_dict[counter] = listy
                # the order bundle should not exceed max_batching_limit
                if len(listy) == max_batching_limit:
                    counter += 1
                    tymSlab = self.order_dict[i][1] + timeband
                    listy = []
                # print("orderbundl_dict", orderbundl_dict)
                i += 1
            else:
                # print("elIf is true")
                tymSlab += timeband
                counter += 1
                listy = []
        print("Final orderbundl_dict", orderbundl_dict)

        for i, k in orderbundl_dict.items():
            print("Attempting to assign an agent to the order bundle", i, k)
            if len(k) < 2:
                newj = self.order_dict[k[0]]
                row = math.ceil((newj[0] * N_CUSTOMER_POINTS) + newj[3])
                lm = point_fboDF.at[row, 'Total_Length']
                print("The assignmentModule, relocateflag, threshold, lm, newj, route", relocateflag, threshold, lm, newj, k)
                self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=k)

            else:
                route, fitness = self.bruteForce_routing(k)
                print("The best route and fitness are", route, fitness)
                trip_time = Model.tym(fitness, MOTORBIKE_KMH)
                print("The tripTym for the best route is", trip_time)
                if trip_time < delivery_time_limit:
                    print("A successful batching is complete")
                    newj = [self.cloudkitchen, self.order_dict[k[0]][1], self.order_dict[k[-1]][2], self.order_dict[route[-1]][3]]
                    lm = fitness
                    print("The assignmentModule, relocateflag, threshold, lm, newj, route",
                        relocateflag, threshold, lm, newj, route)
                    self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=route)
                else:
                    print("The batching order exceeds the delivery time limit")
                    print("eliminating the last stop in the trip route and assigning it individually", route[-1])
                    newj = self.order_dict[route[-1]]
                    row = math.ceil((newj[0] * N_CUSTOMER_POINTS) + newj[3])
                    lm = point_fboDF.at[row, 'Total_Length']
                    print("The assignmentModule, relocateflag, threshold, lm, newj, route",
                          relocateflag, threshold, lm, newj, [route[-1]])
                    self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=[route[-1]])
                    route.pop(-1)
                    print("The new route is", route)
                    if len(route) < 2:
                        newj = self.order_dict[route[0]]
                        row = math.ceil((newj[0] * N_CUSTOMER_POINTS) + newj[3])
                        lm = point_fboDF.at[row, 'Total_Length']
                        print("The assignmentModule, relocateflag, threshold, lm, newj, route", relocateflag, threshold, lm, newj, route)
                        self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=route)
                    else:
                        fitness = self.fitness_mod(route)
                        trip_time = Model.tym(fitness, MOTORBIKE_KMH)
                        print("The tripTym for the best route is", trip_time)
                        if trip_time < delivery_time_limit:
                            print("A successful batching is complete ")
                            newj = [self.cloudkitchen, self.order_dict[route[0]][1], self.order_dict[k[-1]][2], self.order_dict[route[-1]][3]]
                            lm = fitness
                            print("The assignmentModule, relocateflag, threshold, lm, newj, route",
                                relocateflag, threshold, lm, newj, route)
                            self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=route)
                        else:
                            print("The batching order again exceeds the delivery time limit")
                            print("eliminating the last stop in the trip route and assigning it individually", route[-1])
                            newj = self.order_dict[route[-1]]
                            row = math.ceil((newj[0] * N_CUSTOMER_POINTS) + newj[3])
                            lm = point_fboDF.at[row, 'Total_Length']
                            print("The assignmentModule, relocateflag, threshold, lm, newj, route",
                                  relocateflag, threshold, lm, newj, [route[-1]])
                            self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=[route[-1]])
                            route.pop(-1)
                            print("The new route is", route)
                            newj = self.order_dict[route[0]]
                            row = math.ceil((newj[0] * N_CUSTOMER_POINTS) + newj[3])
                            lm = point_fboDF.at[row, 'Total_Length']
                            print("The assignmentModule, relocateflag, threshold, lm, newj, route",
                                relocateflag, threshold, lm, newj, route)
                            self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=route)

        return self.agent_dict

    def assignmentModule(self, relocateflag, threshold, lm, j, routed):
        dmPoint = j[3]
        length = len(routed)
        print("Attempting to assign an agent to the order", j)
        current_time = j[1]
        vehicle = 0
        if lm < threshold:
            vehicle = 1
        fmstart = j[1]
        # weeding out agents whose working hours are over and bicylists who have crossed their daily riding limit
        for id, agent in self.agent_dict.items():
            print("Deactivating agents whose working hours are over ")
            agent.total_working_time = current_time - agent.spawn_time
            print("The agent has been working for", agent.total_working_time)
            print("The agent's work hours are", agent.work_hours)

            if agent.total_working_time > agent.work_hours:
                # print("The agent is deactivated till", 30)
                agent.set_time(30)
                # effectively deactivating the agent if work hours is exceeded
            if agent.vehicle == 1:
                print("Checking the bicycle agent's daily riding distance limit")
                totalKM = sum(agent.first_mile) + sum(agent.last_mile) + sum(agent.dead_mile)
                if totalKM > self.bicycleKMlimit:
                    agent.set_time(30)

        # finding all active agents
        # and adding their IDs to the list
        active_agent_list = Model.active_agents(self.agent_dict, j[1], vehicle)
        # print("The active agents are", active_agent_list)
        actual_waiting_tym = j[2]

        # if active_agent_list is STILL empty, creating new agent
        if not bool(active_agent_list):
            agg = Agent(self.fbo_FID, current_time, vehicle, self.cloudkitchen, self.workhour_limit)
            self.agent_dict[agg.id] = agg
            print("No active agent found, creating agent", agg)
            active_agent_list = [agg.id]
        if vehicle == 0:
            self.orders_fulfilled_bike += length
        else:
            self.orders_fulfilled_bicycle += length
        if relocateflag == 0:
        # finding closest agent with the lowest earning from the active agents who have not relocated
            closest_agent = self.closest_agent_widLowest_earnings_wdoutrelocation(active_agent_list, j[0])
            # print("The closest agent to the FBO", j[0], "is", closest_agent)
            # updating the first and last mile travelled by the agent, when no relocation takes place
            row = math.ceil((j[0] * N_CUSTOMER_POINTS) + self.agent_dict[closest_agent].location)
            fm = point_fboDF.at[row, 'Total_Length']
            final_location = j[3]
            dm = 0
        else:
            # finding closest agent with the lowest earning from the active agents who have relocated
            closest_agent = self.closest_agent_widLowest_earnings(active_agent_list, j[0])
            # print("The closest agent to the FBO", j[0], "is", closest_agent)
            # updating the first and last mile travelled by the agent
            row = math.ceil((self.agent_dict[closest_agent].location * N_FBOS) + j[0])
            fm = fbo_fboDF.at[row, 'Total_Length']
            # After delivering the order, the agent moves to the closest popular FBO
            choice = []
            # the agent relocates to the closest popular FBO

            for fbo, popularity in self.popularity_map.items():
                row = math.ceil((fbo * N_CUSTOMER_POINTS) + dmPoint)
                dist = point_fboDF.at[row, 'Total_Length']
                if popularity != 0:
                    c = (dist ** 2) / popularity
                else:
                    c = 100000000000
                    # c is increased arbitrarily, to reduce chance of selection
                choice.append([fbo, dist, c])
            choice.sort(key=lambda x: x[2])
            final_location = choice[0][0]
            dm = choice[0][1]
            print("The FBO where the agent relocates is", final_location)

        print("Finding the time at which all the orders get prepared and delivery starts for batched orders")
        delivery_start_tym = j[1] + Model.tym(fm, self.agent_dict[closest_agent].velocity) + j[2]
        # the simulation is modelled in this way
        # once an agent reaches the eatery, he has to wait for the designated waiting time period
        # this is irrespective of the time taken to travel the first mile
        if length > 1:
            self.orderBatches.append(length)
            time1 = self.order_dict[routed[0]][1] + self.order_dict[routed[0]][2]
            time2 = self.order_dict[routed[1]][1] + self.order_dict[routed[1]][2]
            if length > 2:
                time3 = self.order_dict[routed[2]][1] + self.order_dict[routed[2]][2]
            else:
                time3 = 0
            # the delivery start time is the latest of the [order i start_tym + order i wait_tym]
            delivery_start_tym = max([time1, time2, time3])
            print("The delivery start time is", delivery_start_tym)
        print("The first, last, and dead mile are", fm, lm, dm)
        dist2 = lm + dm
        ridingtym = Model.tym(fm, self.agent_dict[closest_agent].velocity) + Model.tym(dist2, self.agent_dict[closest_agent].velocity)
        dtym = 0
        if length == 1:
            # the current time is order start time + fm time + waiting time + time taken to travel last and dead mile
            # assuming the agent travels the first mile
            # and reaches the eatery before the start of the waiting time
            current_time = j[1] + j[2] + ridingtym
            dtym = Model.tym(fm, self.agent_dict[closest_agent].velocity) + actual_waiting_tym + Model.tym(lm, self.agent_dict[closest_agent].velocity)
            self.special_delivery_time.append(dtym)
            self.agent_dict[closest_agent].delivery_time.append(dtym)
            lmstart = j[1] + Model.tym(fm, self.agent_dict[closest_agent].velocity) + actual_waiting_tym
            dmstart = j[1] + dtym
        else:
            current_time = delivery_start_tym + Model.tym(dist2, self.agent_dict[closest_agent].velocity)
            # the minimum of the routed is the order that has been placed first
            # for eg. if routed= [2, 1, 0]
            # 0 is the order that has been first placed and therefore first assigned
            # but the shortest route is 2-1-0
            actual_waiting_tym = delivery_start_tym - self.order_dict[min(routed)][1]
            self.special_deliverytime_calculator(routed, delivery_start_tym, self.agent_dict[closest_agent].velocity)
            lmstart = delivery_start_tym
            dmstart = delivery_start_tym + Model.tym(lm, self.agent_dict[closest_agent].velocity)
        self.agent_dict[closest_agent].set_orders_delivered(length)
        self.agent_dict[closest_agent].set_mile(fm, lm, dm, ridingtym, actual_waiting_tym)
        self.agent_dict[closest_agent].set_location(final_location)
        # the agent is inactivated for the time taken to travel first, last & dead mile and waiting time

        print("The agent", closest_agent, "is inactivated till", current_time)
        self.agent_dict[closest_agent].set_time(current_time)

        earning = self.wage_calculator(fm, lm, actual_waiting_tym, self.agent_dict[closest_agent].vehicle, batch_size=length)
        self.agent_dict[closest_agent].update_wage(earning)
        # for batch orders delivery time calculation is different
        self.distVStime_graph(fmstart, fm, lmstart, lm, dmstart, dm, closest_agent)

    def special_deliverytime_calculator(self, route, del_strt_tym, vel):
        l = len(route)
        print("Finding the waiting time for the batch order")

        batch_dist = 0
        c1 = self.cloudkitchen
        c2 = self.order_dict[route[0]][3]
        row = math.ceil((c1 * N_CUSTOMER_POINTS) + c2)
        dist = point_fboDF.at[row, 'Total_Length']
        batch_dist += dist
        # delivery time for first order in the route = time between order placed and del start time + time taken to
        # travel the 'first' last mile
        b_del_time = (del_strt_tym - self.order_dict[route[0]][1]) + Model.tym(batch_dist, vel)
        self.special_delivery_time.append(b_del_time)
        # finding the distance between the first and second order
        # and between the second and third order
        for i in range(l - 1):
            c3 = self.order_dict[route[i]][3]
            c4 = self.order_dict[route[i + 1]][3]
            row = math.ceil((c3 * N_CUSTOMER_POINTS) + c4)
            dist = file4.at[row, 'Total_Length'] / 1000
            batch_dist += dist
            b_del_time = (del_strt_tym - self.order_dict[route[i+1]][1]) + Model.tym(batch_dist, vel)
            self.special_delivery_time.append(b_del_time)

    def order_generator(self):
        order_list = []
        for i in range(self.order_num):
            if self.cloudkitchen == None:
                # The FBO is taken from the sample
                fbo = numpy.random.choice(numpy.arange(0, N_FBOS), p=FBO_POPULARITY_PROB)
            else:
                fbo = self.cloudkitchen
            # print("fbo", fbo)
            points_list = list(range(N_CUSTOMER_POINTS))
            destination = random.choice(points_list)

            # for order time, the hour is taken from the sample distribution
            # And the minute is randomly selected
            start_tym = numpy.random.choice(ORDER_HOUR_SUPPORT, p=ORDER_HOUR_PROB)
            start_tym += random.randrange(0, 100) / 100
            # the wait time at the FBO is taken from the sample
            wt = numpy.random.choice(WAIT_TIME_SUPPORT, p=WAIT_TIME_PROB)
            wait_tym = wt/60

            order_list.append([fbo, start_tym, wait_tym, destination])
        order_list.sort(key=lambda x: x[1])
        counter = 0
        for io in order_list:
            self.order_dict[counter] = io
            counter += 1

    def order_generator_dynamic_serviceArea(self):
        points_list = list(range(N_CUSTOMER_POINTS))
        serviceArea = []
        if self.cloudkitchen == None:
            # The FBO is taken from the sample
            fbo = numpy.random.choice(numpy.arange(0, N_FBOS), p=FBO_POPULARITY_PROB)
        else:
            fbo = self.cloudkitchen
        # print("fbo", fbo)
        for p in points_list:
            row = math.ceil((fbo * N_CUSTOMER_POINTS) + p)
            dist = point_fboDF.at[row, 'Total_Length']
            if dist < self.service_area_radius:
                serviceArea.append(p)
                # selecting all customers within service area radius
        order_list = []
        for i in range(self.order_num):
            destination = random.choice(serviceArea)
            # for order time, the hour is taken from the sample distribution
            # And the minute is randomly selected
            start_tym = numpy.random.choice(ORDER_HOUR_SUPPORT, p=ORDER_HOUR_PROB)
            start_tym += random.randrange(0, 100) / 100
            # the wait time at the FBO is taken from the sample
            wt = numpy.random.choice(WAIT_TIME_SUPPORT, p=WAIT_TIME_PROB)
            wait_tym = wt / 60

            order_list.append([fbo, start_tym, wait_tym, destination])
        order_list.sort(key=lambda x: x[1])
        counter = 0
        for io in order_list:
            self.order_dict[counter] = io
            counter += 1

    def popularity_mapper(self):
        # creating a popularity list for FBOs
        self.popularity_map = {}
        for id in self.fbo_FID:
            # popularity is the number of orders from a FBO in the order_list
            self.popularity_map[id] = 0
            for key, value in self.order_dict.items():
                if value[0] == id:
                    self.popularity_map[id] += 1
        # print("Popularity map", self.popularity_map)

    def closest_agent(self, active_agents, fbo):
        closemat = {}

        if len(active_agents) != 0:
            for agent in active_agents:  # creating distance matrix from cafe to each agent
                row = math.ceil((self.agent_dict[agent].location * N_FBOS) + fbo)
                dist = fbo_fboDF.at[row, 'Total_Length']
                closemat[agent] = dist

            mini = 10000000000000
            mini_key = None
            for key in closemat:
                if mini > closemat[key]:
                    mini = closemat[key]
                    mini_key = key
                else:
                    pass

            return mini_key
        else:
            return None

    def closest_agent_widLowest_earnings(self, active_agents, fbo):
        closemat = []

        if len(active_agents) != 0:
            for agent in active_agents:  # creating distance matrix from cafe to each agent
                row = math.ceil((self.agent_dict[agent].location * N_FBOS) + fbo)
                dist = fbo_fboDF.at[row, 'Total_Length']
                if self.agent_dict[agent].total_working_time == 0:
                    earning_perTime = self.agent_dict[agent].current_earning / 1
                else:
                    earning_perTime = self.agent_dict[agent].current_earning / self.agent_dict[agent].total_working_time
                closemat.append([agent, dist, earning_perTime])

            closemat.sort(key=lambda x: x[1])
            equidist = []
            mindist = closemat[0][1]
            for i in closemat:
                if i[1] == mindist:
                    equidist.append(i)
                else:
                    break
            equidist.sort(key=lambda x: x[2])

            return equidist[0][0]
        else:
            return None

    def wage_calculator(self, fm, lm, wt, vehicle, batch_size):
        if vehicle == 0:
            travelpay = (fm+lm) * 5
            waittimepay = wt * WAIT_TIME_PAY_PER_MIN
            wage = (CUSTOMER_PAY_PER_ORDER*batch_size) + travelpay + waittimepay
        else:
            wage = self.cycle_wage
        return wage

    def bruteForce_routing(self, tripbundl):
        print("Welcome to the bruteForce_routing module")
        if len(tripbundl) == 2:
            chromo1 = [tripbundl[0], tripbundl[1]]
            chromo2 = [tripbundl[1], tripbundl[0]]
            print("The alternate order sequences are", chromo1, chromo2)
            chromo1fitness = self.fitness_mod(chromo1)
            chromo2fitness = self.fitness_mod(chromo2)
            fitnessList = [[chromo1, chromo1fitness], [chromo2, chromo2fitness]]
            fitnessList.sort(key=lambda x: x[1])
            print("Sorted Fitness list", fitnessList)
            return fitnessList[0][0], fitnessList[0][1]
        elif len(tripbundl) == 3:
            chromo1 = [tripbundl[0], tripbundl[1], tripbundl[2]]
            chromo2 = [tripbundl[0], tripbundl[2], tripbundl[1]]
            chromo3 = [tripbundl[1], tripbundl[0], tripbundl[2]]
            chromo4 = [tripbundl[1], tripbundl[2], tripbundl[0]]
            chromo5 = [tripbundl[2], tripbundl[1], tripbundl[0]]
            chromo6 = [tripbundl[2], tripbundl[0], tripbundl[1]]
            print("The alternate order sequences are", chromo1, chromo2, chromo3, chromo4, chromo5, chromo6)
            chromo1fitness = self.fitness_mod(chromo1)
            chromo2fitness = self.fitness_mod(chromo2)
            chromo3fitness = self.fitness_mod(chromo3)
            chromo4fitness = self.fitness_mod(chromo4)
            chromo5fitness = self.fitness_mod(chromo5)
            chromo6fitness = self.fitness_mod(chromo6)
            fitnessList = [[chromo1, chromo1fitness], [chromo2, chromo2fitness], [chromo3, chromo3fitness], [chromo4, chromo4fitness], [chromo5, chromo5fitness], [chromo6, chromo6fitness]]
            fitnessList.sort(key=lambda x: x[1])
            print("Sorted Fitness list", fitnessList)
            return fitnessList[0][0], fitnessList[0][1]

    def fitness_mod(self, chromo):
        # the fitness is the total length of the route
        # the lower the value of the fitness the better
        print("Welcome to the fitness_mod module")
        fitness = 0
        l = len(chromo)
        for i in range(l-1):
            print("calculating intra-link dist between each customer point")
            c1 = self.order_dict[chromo[i]][3]
            c2 = self.order_dict[chromo[i+1]][3]
            row = math.ceil((c1 * N_CUSTOMER_POINTS) + c2)
            dist = file4.at[row, 'Total_Length'] / 1000
            print("customer1, customer2, row, dist", c1, c2, row, dist)
            fitness = fitness + dist
        print("Finding the distance between the cloud kitchen and first customer")
        c3 = self.cloudkitchen
        c4 = self.order_dict[chromo[0]][3]
        row2 = math.ceil((c3 * N_CUSTOMER_POINTS) + c4)
        dist2 = point_fboDF.at[row2, 'Total_Length']
        print("cloudkitchen, customer1, row, dist", c3, c4, row2, dist2)
        fitness = fitness + dist2
        return fitness

    def closest_agent_widLowest_earnings_wdoutrelocation(self, active_agents, fbo):
        closemat = []

        if len(active_agents) != 0:
            for agent in active_agents:  # creating distance matrix from cafe to each agent
                row = math.ceil((fbo * N_CUSTOMER_POINTS) + self.agent_dict[agent].location)
                dist = point_fboDF.at[row, 'Total_Length']
                if self.agent_dict[agent].total_working_time == 0:
                    earning_perTime = self.agent_dict[agent].current_earning / 1
                else:
                    earning_perTime = self.agent_dict[agent].current_earning / self.agent_dict[agent].total_working_time
                closemat.append([agent, dist, earning_perTime])

            closemat.sort(key=lambda x: x[1])
            equidist = []
            mindist = closemat[0][1]
            for i in closemat:
                if i[1] == mindist:
                    equidist.append(i)
                else:
                    break
            equidist.sort(key=lambda x: x[2])

            return equidist[0][0]
        else:
            return None

    def distVStime_graph(self, fmstart, fm, lmstart, lm, dmstart, dm, agent):
        tmiles = sum(self.agent_dict[agent].first_mile) + sum(self.agent_dict[agent].last_mile) + sum(self.agent_dict[agent].dead_mile)
        # recording first mile displacement
        totaldisplacemnt = tmiles - (fm + lm + dm)
        point1 = [fmstart, totaldisplacemnt]
        self.agent_dict[agent].distTimeGraph.append(point1)
        endtime = fmstart + Model.tym(fm, self.agent_dict[agent].velocity)
        totaldisplacemnt = tmiles -lm - dm
        point2 = [endtime, totaldisplacemnt]
        self.agent_dict[agent].distTimeGraph.append(point2)
        # recording last mile displacement
        point3 = [lmstart, totaldisplacemnt]
        self.agent_dict[agent].distTimeGraph.append(point3)
        totaldisplacemnt = tmiles - dm
        point4 = [dmstart, totaldisplacemnt]
        self.agent_dict[agent].distTimeGraph.append(point4)
        # recording dead mile displacement
        endtime = dmstart + Model.tym(dm, self.agent_dict[agent].velocity)
        totaldisplacemnt = tmiles
        point5 = [endtime, totaldisplacemnt]
        self.agent_dict[agent].distTimeGraph.append(point5)

        return

    @classmethod
    def active_agents(cls, agentdict, order_time, vehicle):
        active_agents = []
        for i, j in agentdict.items():                      # selecting an agent j
            if j.time <= order_time and j.vehicle == vehicle:                        # checking whether agent j's inactive till time is less than the time at of order generation
                active_agents.append(i)                     # if condition is true the agent is added to the active list
            else:
                pass

        return active_agents

    @classmethod
    def scatter_plotter(cls, list1=[], list2=[], list3=[], list4=[]):
        def parser(list):
            if list != None:
                x = []
                y = []
                for i in range(len(list)):
                    x.append(list[i][0])

                for i in range(len(list)):
                    y.append(list[i][1])
                return x, y
            else:
                pass

        x1, y1 = parser(list1)
        x2, y2 = parser(list2)
        x3, y3 = parser(list3)
        x4, y4 = parser(list4)
        plt.scatter(x1, y1, s=10, c='y', marker="o", label='1')
        plt.scatter(x2, y2, s=10, c='g', marker="x", label='2')
        plt.scatter(x3, y3, s=10, c='b', marker="*", label='3')
        plt.scatter(x4, y4, s=10, c='c', marker="s", label='4')
        plt.show()

    @staticmethod
    def tym(dista, vel):
        return dista / vel


if __name__ == "__main__":
    # ######################
    fleetsize = []
    ordersfulfilledbikes = 0
    ordersfulfilledbicycles = 0
    orderBatches = []
    first_mile_list = []
    last_mile_list = []
    dead_mile_list = []
    shift9 = []
    shift12 = []
    shift16 = []
    shift19 = []
    shift9c = []
    shift12c = []
    shift16c = []
    shift19c = []
    cycles = []
    iterations = 30
    chosenBicycleAgent = None
    for k in range(iterations):
        shift9s = 0
        shift12s = 0
        shift16s = 0
        shift19s = 0
        shift9sc = 0
        shift12sc = 0
        shift16sc = 0
        shift19sc = 0
        cycle = 0
        a = Model(100, cloudkitchen=None, cyclewage=15, bicycleKMlimit=500, sar=None, workhourLimit=100)
        agent_dict = a.modelRun(relocateflag=1, threshold=0, timeband=0.083, delivery_time_limit=0.75, max_batching_limit=3)
        ordersfulfilledbikes += a.orders_fulfilled_bike
        ordersfulfilledbicycles += a.orders_fulfilled_bicycle
        orderBatches += a.orderBatches
        agent_join_tym = []
        for i, j in agent_dict.items():
            first_mile_list += j.first_mile
            last_mile_list += j.last_mile
            dead_mile_list += j.dead_mile


            if j.spawn_time < 12:
                if j.vehicle == 0:
                    shift9s = shift9s + 1
                else:
                    shift9sc = shift9sc + 1
                    if j.work_hours > 12:
                        chosenBicycleAgent = j

            elif j.spawn_time > 12 and j.spawn_time < 16:
                if j.vehicle == 0:
                    shift12s = shift12s + 1
                else:
                    shift12sc = shift12sc + 1
            elif j.spawn_time > 16 and j.spawn_time < 19:
                if j.vehicle == 0:
                    shift16s = shift16s + 1
                else:
                    shift16sc = shift16sc + 1
            elif j.spawn_time > 19:
                if j.vehicle == 0:
                    shift19s = shift19s + 1
                else:
                    shift19sc = shift19sc + 1
        ts = shift9s + shift12s + shift16s + shift19s
        fleetsize.append([k, ts])
        shift9.append(shift9s)
        shift12.append(shift12s)
        shift16.append(shift16s)
        shift19.append(shift19s)
        shift9c.append(shift9sc)
        shift12c.append(shift12sc)
        shift16c.append(shift16sc)
        shift19c.append(shift19sc)
        cycles.append(cycle)
    print("*****************************************************************")
    #print("Avg. first mile", statistics.mean(first_mile_list))
    #print("Avg. last mile", statistics.mean(last_mile_list))
    last_mile_list.sort(reverse=True)
    #print(last_mile_list)
    print("Avg. dead mile", statistics.mean(dead_mile_list))
    print("Batched Orders", sum(orderBatches), orderBatches)
    print("Shiftwise",statistics.mean(shift9), statistics.mean(shift12), statistics.mean(shift19))
    print("Shift@9", statistics.mean(shift9), statistics.stdev(shift9))
    print("Shift@12", statistics.mean(shift12), statistics.stdev(shift12))
    print("Shift@16", statistics.mean(shift16), statistics.stdev(shift16))
    print("Shift@19", statistics.mean(shift19), statistics.stdev(shift19))
    print("ordersfulfilled bikes", ordersfulfilledbikes)
    print("Cycles")
    print("Shift@9cycles", statistics.mean(shift9c), statistics.stdev(shift9c))
    print("Shift@12cycles", statistics.mean(shift12c), statistics.stdev(shift12c))
    print("Shift@16cycles", statistics.mean(shift16c), statistics.stdev(shift16c))
    print("Shift@19cycles", statistics.mean(shift19c), statistics.stdev(shift19c))
    print("ordersfulfilled bicycles", ordersfulfilledbicycles)
    fleetsize.sort(key=lambda x: x[1])
    print(fleetsize)
    #distVStimeDF = pd.DataFrame(chosenBicycleAgent.distTimeGraph, columns=['x', 'y'])
    #distVStimeDF.to_excel("FleetTestdistVStimeGraph2.xlsx")
    # --- Write fleet sizes for Step 2 handoff ---
    os.makedirs("outputs", exist_ok=True)
    fleet_means = {
        "bike": {
            9: statistics.mean(shift9),
            12: statistics.mean(shift12),
            16: statistics.mean(shift16),
            19: statistics.mean(shift19),
        },
        "bicycle": {
            9: statistics.mean(shift9c),
            12: statistics.mean(shift12c),
            16: statistics.mean(shift16c),
            19: statistics.mean(shift19c),
        },
    }
    with open("outputs/fleet_sizes.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["vehicle", "shift_hour", "mean_fleet_size", "ceil_fleet_size"])
        for vehicle, shifts in fleet_means.items():
            for hour, mean_val in shifts.items():
                writer.writerow([vehicle, hour, mean_val, math.ceil(mean_val)])
    print("Fleet sizes written to outputs/fleet_sizes.csv")