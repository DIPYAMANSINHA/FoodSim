# Step 2: Multi-day simulation of food delivery operations using the
# shift-wise fleet sizes determined by step1. Produces emissions per
# delivery, parking demand, and income distribution under a given pay
# structure.
#
# Code accompanying:
#   Sinha, D., & Pandit, D. (2023). Assessing the economic sustainability
#   of gig work: A case of hyper-local food delivery workers in Kolkata,
#   India. Research in Transportation Economics, 100, 101335.

import math
import random
import statistics

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
    def __init__(self, fbo_FID, tim, w, vehicle, cloudkitchen, workhourlimit):
        self.vehicle = vehicle  # 0 is bike, 1 is cycle, 0 set as default
        self.cloudkitchen = cloudkitchen
        if vehicle == 0:
            self.velocity = MOTORBIKE_KMH  # bike velocity
        else:
            self.velocity = BICYCLE_KMH  # cycle velocity
        if cloudkitchen == None:
            self.location = numpy.random.choice(numpy.arange(0, N_FBOS), p=FBO_POPULARITY_PROB)
        else:
            self.location = cloudkitchen
        self.id = Agent.id_counter
        Agent.id_counter += 1
        self.time = 0
        self.first_mile = []
        self.last_mile = []
        self.dead_mile = []
        self.till_last_day_total_mile = 0
        self.wait_time = []
        self.delivery_time = []
        self.weeklyIncentives = []
        self.total_waiting_time = 0
        self.orders_delivered = 0
        self.days_earning = 0
        self.total_earning = 0
        self.total_riding_time = 0
        self.total_working_time = 0
        self.spawn_time = tim
        self.distTimeGraph = []
        # if the workhour exceeds the workhourlimit, it is set to the maximum
        if workhourlimit != None:
            if w > workhourlimit:
                w = workhourlimit - 1
        self.work_hours = w + (random.randrange(0, 100) / 100)
        self.till_last_week_earning = 0
        self.entry_time = 0
        self.parking_status = 0
        # creating a dictionary skeleton for storing FBO wise parking load
        self.parkingLoad_agentwise = {x:0 for x in range(N_FBOS) if x == x}
        print("The parking load is", self.id, self.parkingLoad_agentwise)
        self.last_day_location = None


    def set_mile(self, fm, sm, tm, ridingtym, act_wait_tym):
        """Once an order is assigned
            The total 1st mile, 2nd mile and 3rd mile is updated.
                """
        self.first_mile.append(fm)
        self.last_mile.append(sm)
        self.dead_mile.append(tm)
        # print("The agent's riding time till now was", self.total_riding_time)
        self.total_riding_time += ridingtym
        self.total_waiting_time += act_wait_tym
        # print("The agent's active time till now is", self.total_riding_time)

    def set_newday(self):
        print("Welcome to the newday module")
        # updating last days's parking for agents whose parking status did not automatically close
        if self.parking_status == 0:
            if (self.spawn_time + self.work_hours) < 24:
                endtime = max((self.spawn_time + self.work_hours), self.entry_time)
            elif self.entry_time < 24:
                endtime = 24
            else:
                endtime = self.entry_time
            self.parkingupdater(self.last_day_location, 1, endtime)
        ############
        self.total_working_time = 0
        self.time = self.spawn_time
        daily_incentive = self.set_incentives()
        self.total_earning = self.total_earning + self.days_earning + daily_incentive
        self.days_earning = 0
        self.till_last_day_total_mile = sum(self.first_mile) + sum(self.last_mile) + sum(self.dead_mile)
        # new day new location
        if self.cloudkitchen == None:
            self.location = numpy.random.choice(numpy.arange(0, N_FBOS), p=FBO_POPULARITY_PROB)
        else:
            self.location = self.cloudkitchen
        # updating new day's parking
        self.parkingupdater(self.location, 0, self.spawn_time)

    def set_incentives(self):
        incentives = 0
        print("Welcome to daily incentive module")
        print("Agent", self.id, "'s Days earning is", self.days_earning)
        if self.days_earning > 325 and self.days_earning < 475:
            incentives = 75
        elif self.days_earning > 475 and self.days_earning < 800:
            incentives = 125
        elif self.days_earning > 800:
            incentives = 250
        print("Agent", self.id, "'s Days daily incentive is", incentives)
        return incentives

    def parkingupdater(self, fbo, status, time):

        if status == 0:
            print("The agent",self.id, "enters eatery ", fbo, "at time ", time)
            self.entry_time = time
            self.last_day_location =fbo
            self.parking_status = 0
        else:
            print("The agent",self.id, "exits eatery ", fbo, "at time ", time)
            pl = time - self.entry_time
            print("The agent", self.id, "creates a parking load of ", pl, "at eatery ", fbo)
            self.parkingLoad_agentwise[fbo] += round(pl, 2)
            print(self.parkingLoad_agentwise)
            self.parking_status = 1

    def weekly_incentive(self, week):
        print("Welcome to weekly incentive module for week", week)
        print("Agent", self.id, "'s till last week total earning is", self.till_last_week_earning)
        print("Agent", self.id, "'s total earning is", self.total_earning)
        if self.till_last_week_earning == 0:
            self.till_last_week_earning = self.total_earning
            last_week_earning = self.total_earning
        else:
            last_week_earning = self.total_earning - self.till_last_week_earning
            self.till_last_week_earning = self.total_earning
        print("Agent", self.id, "'s last week earning is", last_week_earning)
        w_incentive = 0
        if last_week_earning >= 600 and last_week_earning < 2700:
            w_incentive = 200
        if last_week_earning >= 2700:
            w_incentive = 600
        self.weeklyIncentives.append(w_incentive)
        print("Agent", self.id, "'s weekly incentive is", w_incentive)

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
        self.days_earning = self.days_earning + earning

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
    def __init__(self, order_num, shiftvol, cloudkitchen, wagerate, minWage, bicycleKMlimit, sar, workhourLimit):
        self.fbo_FID = list(range(N_FBOS))
        self.order_num = order_num
        self.agent_dict = {}
        self.order_dict = {}
        self.sl = 0
        self.order_delayed_by = []
        self.shiftvol = shiftvol
        self.orders_fulfilled_bike = 0
        self.orders_fulfilled_bicycle = 0
        self.orderBatches = []
        self.special_delivery_time = []
        self.cloudkitchen = cloudkitchen
        self.minWage = minWage
        self.wageRate = wagerate
        self.orderDelivery_vehicle = []
        self.bicycleKMlimit = bicycleKMlimit
        self.service_area_radius = sar
        self.workhourLimit = workhourLimit
        self.agent_creator(self.workhourLimit)

    def modelRun(self, relocateflag, threshold, timeband, delivery_time_limit, max_batching_limit):
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
                # the order bundle should not exceed three orders
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
                #print("The assignmentModule, relocateflag, threshold, lm, newj, route", relocateflag, threshold, lm, newj, k)
                self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=k)

            else:
                route, fitness = self.bruteForce_routing(k)
                #print("The best route and fitness are", route, fitness)
                trip_time = Model.tym(fitness, MOTORBIKE_KMH)
                #print("The tripTym for the best route is", trip_time)
                if trip_time < delivery_time_limit:
                    #print("A successful batching is complete")
                    # newj[2] is not required & used, but still passed
                    # the start time of the order is the start time of the first order
                    newj = [self.cloudkitchen, self.order_dict[k[0]][1], self.order_dict[k[-1]][2], self.order_dict[route[-1]][3]]
                    lm = fitness
                    #print("The assignmentModule, relocateflag, threshold, lm, newj, route", relocateflag, threshold, lm, newj, route)
                    self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=route)
                else:
                    #print("The batching order exceeds the delivery time limit")
                    #print("eliminating the last stop in the trip route and assigning it individually", route[-1])
                    newj = self.order_dict[route[-1]]
                    row = math.ceil((newj[0] * N_CUSTOMER_POINTS) + newj[3])
                    lm = point_fboDF.at[row, 'Total_Length']
                    #print("The assignmentModule, relocateflag, threshold, lm, newj, route", relocateflag, threshold, lm, newj, [route[-1]])
                    self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=[route[-1]])
                    route.pop(-1)
                    #print("The new route is", route)
                    if len(route) < 2:
                        newj = self.order_dict[route[0]]
                        row = math.ceil((newj[0] * N_CUSTOMER_POINTS) + newj[3])
                        lm = point_fboDF.at[row, 'Total_Length']
                        #print("The assignmentModule, relocateflag, threshold, lm, newj, route", relocateflag, threshold, lm, newj, route)
                        self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=route)
                    else:
                        fitness = self.fitness_mod(route)
                        trip_time = Model.tym(fitness, MOTORBIKE_KMH)
                        #print("The tripTym for the best route is", trip_time)
                        if trip_time < delivery_time_limit:
                            #print("A successful batching is complete ")
                            # the first order in a route is the order with the minimum index
                            newj = [self.cloudkitchen, self.order_dict[min(route)][1], self.order_dict[route[-1]][2], self.order_dict[route[-1]][3]]
                            lm = fitness
                            #print("The assignmentModule, relocateflag, threshold, lm, newj, route", relocateflag, threshold, lm, newj, route)
                            self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=route)
                        else:
                            #print("The batching order again exceeds the delivery time limit")
                            #print("eliminating the last stop in the trip route and assigning it individually", route[-1])
                            newj = self.order_dict[route[-1]]
                            row = math.ceil((newj[0] * N_CUSTOMER_POINTS) + newj[3])
                            lm = point_fboDF.at[row, 'Total_Length']
                            #print("The assignmentModule, relocateflag, threshold, lm, newj, route", relocateflag, threshold, lm, newj, [route[-1]])
                            self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=[route[-1]])
                            route.pop(-1)
                            #print("The new route is", route)
                            newj = self.order_dict[route[0]]
                            row = math.ceil((newj[0] * N_CUSTOMER_POINTS) + newj[3])
                            lm = point_fboDF.at[row, 'Total_Length']
                            #print("The assignmentModule, relocateflag, threshold, lm, newj, route", relocateflag, threshold, lm, newj, route)
                            self.assignmentModule(relocateflag, threshold, lm, j=newj, routed=route)

        self.newday()


    def newday(self):
        for m, n in self.agent_dict.items():
            n.set_newday()

    def assignmentModule(self, relocateflag, threshold, lm, j, routed):
        dmPoint = j[3]
        length = len(routed)
        print("Attempting to assign an agent to the order", j)
        current_time = j[1]
        fmstart = 0
        lmstart = 0
        dmstart = 0

        # weeding out agents whose working hours are over and cyclists whose daily riding limit is over
        for id, agent in self.agent_dict.items():
            print("Deactivating agents whose working hours are over ")
            agent.total_working_time = current_time - agent.spawn_time
            # print("The agent has been working for", agent.total_working_time)
            # print("The agent's work hours are", agent.work_hours)
            if agent.total_working_time > agent.work_hours:
                print("The agent is deactivated till", 30)
                agent.set_time(30)
                # effectively deactivating the agent for today if work hours is exceeded

            if agent.vehicle == 1:
                print("Checking the bicycle agent's daily riding time limit")
                totalKMtoday = sum(agent.first_mile) + sum(agent.last_mile) + sum(agent.dead_mile) - agent.till_last_day_total_mile
                if totalKMtoday > self.bicycleKMlimit:
                    agent.set_time(30)

        vehicle = 0
        if lm < threshold:
            vehicle = 1
        # finding all active agents
        # and adding their IDs to the list
        active_agent_list = Model.active_agents(self.agent_dict, j[1], vehicle)
        fmstart = j[1]
        # print("The active agents are", active_agent_list)
        actual_waiting_tym = j[2]
        # if active agent list is empty, trying to find an alternate only in case of a bicycle
        if not bool(active_agent_list):
            if vehicle == 1:
                vehicle = 0
            active_agent_list = Model.active_agents(self.agent_dict, j[1], vehicle)
            if not bool(active_agent_list):
                print("No active agent found, skipping order*******************************************************************************************")
                return
        if vehicle == 0:
            self.orders_fulfilled_bike += length
        else:
            self.orders_fulfilled_bicycle += length

        if relocateflag == 0:
        # finding closest agent with the lowest earning from the active agents who have not relocated
            closest_agent = self.closest_agent_widLowest_earnings_wdoutrelocation(active_agent_list, j[0])
            # updating the parking load as the vehicle exits the eatery
            self.agent_dict[closest_agent].parkingupdater(self.agent_dict[closest_agent].location, 1, current_time)
            # print("The closest agent to the FBO", j[0], "is", closest_agent)
            # updating the first and last mile travelled by the agent, when no relocation takes place
            row = math.ceil((j[0] * N_CUSTOMER_POINTS) + self.agent_dict[closest_agent].location)
            fm = point_fboDF.at[row, 'Total_Length']
            #print("The first mile traveled is", fm)
            #print("The last mile traveled is", lm)
            final_location = j[3]
            dm = 0
        else:
        # finding closest agent with the lowest earning from the active agents who have relocated
            closest_agent = self.closest_agent_widLowest_earnings(active_agent_list, j[0])
            # updating the parking load as the vehicle exits the eatery
            self.agent_dict[closest_agent].parkingupdater(self.agent_dict[closest_agent].location, 1, current_time)
            # updating the first and last mile travelled by the agent
            row = math.ceil((self.agent_dict[closest_agent].location * N_FBOS) + j[0])
            fm = fbo_fboDF.at[row, 'Total_Length']
            #print("The first mile traveled is", fm)
            #print("The last mile traveled is", lm)
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
            #print("The FBO where the agent relocates is", final_location)

        #print("Finding the time at which all the orders get prepared and delivery starts for batched orders")
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
            # delivery start time is the latest of (the order placed time+wait time)
            delivery_start_tym = max([time1, time2, time3])
            #print("The delivery start time is", delivery_start_tym)
        #print("The first, last, and dead mile are", fm, lm, dm)

        dist2 = lm + dm
        ridingtym = Model.tym(fm, self.agent_dict[closest_agent].velocity) + Model.tym(dist2, self.agent_dict[closest_agent].velocity)
        dtym = 0
        if length == 1:
            # the current time is order start time + fm time + waiting time + time taken to travel last and dead mile
            # assuming the agent travels the first mile before within the order prep time
            # and reaches the eatery before the start of the waiting time
            current_time = j[1] + ridingtym + j[2]
            dtym = Model.tym(fm, self.agent_dict[closest_agent].velocity) + Model.tym(lm, self.agent_dict[closest_agent].velocity) + j[2]
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
        # updating the parking demand for the waiting at the eatery
        self.agent_dict[closest_agent].parkingupdater(j[0], 0, 0)
        self.agent_dict[closest_agent].parkingupdater(j[0], 1, actual_waiting_tym)
        self.agent_dict[closest_agent].set_orders_delivered(length)
        self.agent_dict[closest_agent].set_mile(fm, lm, dm, ridingtym, actual_waiting_tym)
        self.agent_dict[closest_agent].set_location(final_location)
        # the agent is inactivated for the time taken to travel first, last & dead mile and waiting time
        # updating the parking load as the vehicle enters the eatery for parking after delivery and relocation
        self.agent_dict[closest_agent].parkingupdater(self.agent_dict[closest_agent].location, 0, current_time)

        print("The agent", closest_agent, "is inactivated till", current_time)
        self.agent_dict[closest_agent].set_time(current_time)

        self.agent_dict[closest_agent].wait_time.append(actual_waiting_tym)
        earning = self.wage_calculator(fm, lm, actual_waiting_tym, self.agent_dict[closest_agent].vehicle, batchsize=length)
        self.agent_dict[closest_agent].update_wage(earning)
        # for batch orders delivery time calculation is different
        self.distVStime_graph(fmstart, fm, lmstart, lm, dmstart, dm, closest_agent)

    def distVStime_graph(self, fmstart, fm, lmstart, lm, dmstart, dm, agent):
        tmiles = sum(self.agent_dict[agent].first_mile) + sum(self.agent_dict[agent].last_mile) + sum(self.agent_dict[agent].dead_mile)
        # recording pre-first mile displacement
        totaldisplacemnt = tmiles - (self.agent_dict[agent].till_last_day_total_mile + fm + lm + dm)
        point1 = [fmstart, totaldisplacemnt]
        self.agent_dict[agent].distTimeGraph.append(point1)
        endtime = fmstart + Model.tym(fm, self.agent_dict[agent].velocity)
        totaldisplacemnt = tmiles - (self.agent_dict[agent].till_last_day_total_mile + lm + dm)
        # recording first mile displacement
        point2 = [endtime, totaldisplacemnt]
        self.agent_dict[agent].distTimeGraph.append(point2)
        # recording pre-last mile displacement or waiting time at eatery
        point3 = [lmstart, totaldisplacemnt]
        self.agent_dict[agent].distTimeGraph.append(point3)
        # recording last-mile displacement
        totaldisplacemnt = tmiles - (self.agent_dict[agent].till_last_day_total_mile + dm)
        point4 = [dmstart, totaldisplacemnt]
        self.agent_dict[agent].distTimeGraph.append(point4)
        # recording dead mile displacement
        endtime = dmstart + Model.tym(dm, self.agent_dict[agent].velocity)
        totaldisplacemnt = tmiles - self.agent_dict[agent].till_last_day_total_mile
        point5 = [endtime, totaldisplacemnt]
        self.agent_dict[agent].distTimeGraph.append(point5)
        return

    def special_deliverytime_calculator(self, route, del_strt_tym, vel):
        l = len(route)
        #print("Finding the waiting time for the batch order")
        delivery_start_tym = 0

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
        for i in range(l - 1):
            c3 = self.order_dict[route[i]][3]
            c4 = self.order_dict[route[i + 1]][3]
            row = math.ceil((c3 * N_CUSTOMER_POINTS) + c4)
            dist = file4.at[row, 'Total_Length'] / 1000
            batch_dist += dist
            b_del_time = (del_strt_tym - self.order_dict[route[i+1]][1]) + Model.tym(batch_dist, vel)
            self.special_delivery_time.append(b_del_time)

    def bruteForce_routing(self, tripbundl):
        #print("Welcome to the bruteForce_routing module")
        if len(tripbundl) == 2:
            chromo1 = [tripbundl[0], tripbundl[1]]
            chromo2 = [tripbundl[1], tripbundl[0]]
            #print("The alternate order sequences are", chromo1, chromo2)
            chromo1fitness = self.fitness_mod(chromo1)
            chromo2fitness = self.fitness_mod(chromo2)
            fitnessList = [[chromo1, chromo1fitness], [chromo2, chromo2fitness]]
            fitnessList.sort(key=lambda x: x[1])
            #print("Sorted Fitness list", fitnessList)
            return fitnessList[0][0], fitnessList[0][1]
        elif len(tripbundl) == 3:
            chromo1 = [tripbundl[0], tripbundl[1], tripbundl[2]]
            chromo2 = [tripbundl[0], tripbundl[2], tripbundl[1]]
            chromo3 = [tripbundl[1], tripbundl[0], tripbundl[2]]
            chromo4 = [tripbundl[1], tripbundl[2], tripbundl[0]]
            chromo5 = [tripbundl[2], tripbundl[1], tripbundl[0]]
            chromo6 = [tripbundl[2], tripbundl[0], tripbundl[1]]
            #print("The alternate order sequences are", chromo1, chromo2, chromo3, chromo4, chromo5, chromo6)
            chromo1fitness = self.fitness_mod(chromo1)
            chromo2fitness = self.fitness_mod(chromo2)
            chromo3fitness = self.fitness_mod(chromo3)
            chromo4fitness = self.fitness_mod(chromo4)
            chromo5fitness = self.fitness_mod(chromo5)
            chromo6fitness = self.fitness_mod(chromo6)
            fitnessList = [[chromo1, chromo1fitness], [chromo2, chromo2fitness], [chromo3, chromo3fitness], [chromo4, chromo4fitness], [chromo5, chromo5fitness], [chromo6, chromo6fitness]]
            fitnessList.sort(key=lambda x: x[1])
            #print("Sorted Fitness list", fitnessList)
            return fitnessList[0][0], fitnessList[0][1]

    def fitness_mod(self, chromo):
        # the fitness is the total length of the route
        # the lower the value of the fitness the better
        #print("Welcome to the fitness_mod module")
        fitness = 0
        l = len(chromo)
        for i in range(l-1):
            #print("calculating intra-link dist between each customer point")
            c1 = self.order_dict[chromo[i]][3]
            c2 = self.order_dict[chromo[i+1]][3]
            row = math.ceil((c1 * N_CUSTOMER_POINTS) + c2)
            dist = file4.at[row, 'Total_Length'] / 1000
            #print("customer1, customer2, row, dist", c1, c2, row, dist)
            fitness = fitness + dist
        #print("Finding the distance between the cloud kitchen and first customer")
        c3 = self.cloudkitchen
        c4 = self.order_dict[chromo[0]][3]
        row2 = math.ceil((c3 * N_CUSTOMER_POINTS) + c4)
        dist2 = point_fboDF.at[row2, 'Total_Length']
        #print("cloudkitchen, customer1, row, dist", c3, c4, row2, dist2)
        fitness = fitness + dist2
        return fitness

    def agent_creator(self, workhourLimit):
        totalagents = sum(self.shiftvol[0] + self.shiftvol[1])
        # this is the probability of the daily work hours
        p = WORK_HOURS_PROB
        workhour_wise_agents = []
        for i in p:
            workhour_wise_agents.append(math.ceil(i * totalagents))
        # the multiplication of the probability and total agents and their ceil is creating more agents
        # than the total agents required
        # this needs to be rebalanced
        #print(workhour_wise_agents)
        s = sum(workhour_wise_agents)
        ade = 0
        # to rebalance this 1 agent is reduced from the upper end of the worrkhour_wise_agents list one by one
        # till it gets equal to the totalagents
        while s != totalagents:
            workhour_wise_agents[ade] = workhour_wise_agents[ade] - 1
            s = sum(workhour_wise_agents)
            ade = ade + 1
        #print("Rebalanced workhour_wise_agents")
        # Expanding the workhour_wise_agents into the list 'hours'
        hour = []
        h = 1
        for i in workhour_wise_agents:
            for j in range(i):
                hour.append(h)
            h = h + 1
        #print("Distribution of work hours", hour)
        # selecting the last work hours in the list
        # i.e. assigning the longer work hours at the end first
        sthour = len(hour) - 1
        for i in range(self.shiftvol[0][0]):
            # spawning bikes
            w = hour[sthour]
            sthour = sthour - 1
            vehicle = 0
            agg = Agent(self.fbo_FID, 9, w, vehicle, self.cloudkitchen, workhourLimit)
            agg.time = 9
            self.agent_dict[agg.id] = agg
            # updating the parking load as the vehicle enters the eatery for parking
            agg.parkingupdater(agg.location, 0, 9)
        for i in range(self.shiftvol[1][0]):
            # spawning cycles
            w = hour[sthour]
            sthour = sthour - 1
            vehicle = 1
            agg = Agent(self.fbo_FID, 9, w, vehicle, self.cloudkitchen, workhourLimit)
            agg.time = 9
            self.agent_dict[agg.id] = agg
            # updating the parking load as the vehicle enters the eatery for parking
            agg.parkingupdater(agg.location, 0, 9)

        for i in range(self.shiftvol[0][1]):
            # spawning bikes
            w = hour[sthour]
            sthour = sthour - 1
            vehicle = 0
            agg = Agent(self.fbo_FID, 12, w, vehicle, self.cloudkitchen, workhourLimit)
            agg.time = 12
            self.agent_dict[agg.id] = agg
            # updating the parking load as the vehicle enters the eatery for parking
            agg.parkingupdater(agg.location, 0, 12)

        for i in range(self.shiftvol[1][1]):
            # spawning cycles
            w = hour[sthour]
            sthour = sthour - 1
            vehicle = 1
            agg = Agent(self.fbo_FID, 12, w, vehicle, self.cloudkitchen, workhourLimit)
            agg.time = 12
            self.agent_dict[agg.id] = agg
            # updating the parking load as the vehicle enters the eatery for parking
            agg.parkingupdater(agg.location, 0, 12)

        for i in range(self.shiftvol[0][2]):
            # spawning bikes
            w = hour[sthour]
            sthour = sthour - 1
            vehicle = 0
            agg = Agent(self.fbo_FID, 16, w, vehicle, self.cloudkitchen, workhourLimit)
            agg.time = 16
            self.agent_dict[agg.id] = agg
            # updating the parking load as the vehicle enters the eatery for parking
            agg.parkingupdater(agg.location, 0, 16)

        for i in range(self.shiftvol[1][2]):
            # spawning cycles
            w = hour[sthour]
            sthour = sthour - 1
            vehicle = 1
            agg = Agent(self.fbo_FID, 16, w, vehicle, self.cloudkitchen, workhourLimit)
            agg.time = 16
            self.agent_dict[agg.id] = agg
            # updating the parking load as the vehicle enters the eatery for parking
            agg.parkingupdater(agg.location, 0, 16)

        for i in range(self.shiftvol[0][3]):
            # spawning bikes
            w = hour[sthour]
            sthour = sthour - 1
            vehicle = 0
            agg = Agent(self.fbo_FID, 19, w, vehicle, self.cloudkitchen, workhourLimit)
            agg.time = 19
            self.agent_dict[agg.id] = agg
            # updating the parking load as the vehicle enters the eatery for parking
            agg.parkingupdater(agg.location, 0, 19)

        for i in range(self.shiftvol[1][3]):
            # spawning cycles
            w = hour[sthour]
            sthour = sthour - 1
            vehicle = 1
            agg = Agent(self.fbo_FID, 19, w, vehicle, self.cloudkitchen, workhourLimit)
            agg.time = 19
            self.agent_dict[agg.id] = agg
            # updating the parking load as the vehicle enters the eatery for parking
            agg.parkingupdater(agg.location, 0, 19)

    def order_generator(self):
        order_list = []
        for i in range(self.order_num):

            # The FBO is taken from the sample
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
        #print("Welcome inside closest_agent_widLowest_earnings")
        closemat = []
        # print("The active agents are", active_agents)
        if len(active_agents) != 0:
            for agent in active_agents:  # creating distance matrix from cafe to each agent
                # print("For", agent, "in active agents")
                row = (self.agent_dict[agent].location * N_FBOS) + fbo
                # print("Row", ((self.agent_dict[agent].location * N_FBOS) + fbo))
                dist = round(fbo_fboDF.at[row, 'Total_Length'])
                # print("Distance", dist)
                # print("Earnings", self.agent_dict[agent].days_earning)
                # print("Total working time", self.agent_dict[agent].total_working_time)
                if self.agent_dict[agent].total_working_time == 0:
                    earning_perTime = 0
                else:
                    earning_perTime = self.agent_dict[agent].days_earning / self.agent_dict[agent].total_working_time
                # print("Agent, dist, earning_per_time", [agent, dist, earning_perTime])
                closemat.append([agent, dist, earning_perTime])

            closemat.sort(key=lambda x: x[1])
            # print("Closemat", closemat)
            equidist = []
            mindist = closemat[0][1]
            for i in closemat:
                if i[1] == mindist:
                    equidist.append(i)
                else:
                    break
            equidist.sort(key=lambda x: x[2])
            #print("Equidist", equidist)
            # print("The closest agent with lowest earnings", equidist[0][0])
            return equidist[0][0]
        else:
            return None

    def closest_agent_widLowest_earnings_wdoutrelocation(self, active_agents, fbo):
        closemat = []

        if len(active_agents) != 0:
            for agent in active_agents:  # creating distance matrix from cafe to each agent
                row = math.ceil((fbo * N_CUSTOMER_POINTS) + self.agent_dict[agent].location)
                dist = point_fboDF.at[row, 'Total_Length']
                if self.agent_dict[agent].total_working_time == 0:
                    earning_perTime = self.agent_dict[agent].days_earning / 1
                else:
                    earning_perTime = self.agent_dict[agent].days_earning / self.agent_dict[agent].total_working_time
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

    def wage_calculator(self, fm, lm, wt, vehicle, batchsize):

        travelpay = (fm + lm) * self.wageRate
        waittimepay = wt * WAIT_TIME_PAY_PER_MIN
        wage = (CUSTOMER_PAY_PER_ORDER*batchsize) + travelpay + waittimepay
        if wage < self.minWage:
            wage = self.minWage
        return wage

    @classmethod
    def active_agents(cls, agentdict, order_time, vehicle):
        active_agents = []
        for i, j in agentdict.items():                      # selecting an agent j
            if j.time <= order_time and j.vehicle == vehicle:
                # checking whether agent j's inactive till time is less than the time at of order generation
                # and the agent belongs to the same vehicle category
                active_agents.append(i)
                # if condition is true the agent is added to the active list
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
        return (dista / vel)


if __name__ == "__main__":
    #########################################################
    cycles = 0
    bikes = 0
    orderDelivery_Vehicle = []
    first_mile_bike = []
    last_mile_bike = []
    dead_mile_bike = []
    parkingLoad_bicycle = []
    parked_time_ratio_bike = []
    idleTymratioBike = []
    del_tym_bike = []
    first_mile_cycle = []
    last_mile_cycle = []
    dead_mile_cycle = []
    parkingLoad_bike = []
    parked_time_ratio_cycle = []
    idleTymratioCycle = []
    del_tym_cycle = []
    agentearning = []
    agentearningperhourBike = []
    agentearningperhourBicycle = []
    earningtablebike = []
    earningtablebiycle = []
    order_delay = []
    orderskipped = 0
    iterations = 30
    orderVol = 500
    shiftvol = [[18, 20, 0, 9], [0, 0, 0, 0]]
    mbl = 1
    r = None
    wagerate = 5
    ###############################################################################################################################
    # this is where the first set of input goes
    a = Model(orderVol, shiftvol, cloudkitchen=None, wagerate=wagerate, minWage=15, bicycleKMlimit=500, sar=None, workhourLimit=None)
    for p in range(iterations):
        ###############################################################################################################################
        # this is where the second and last set of input goes
        a.modelRun(relocateflag=1, threshold=0, timeband=0.083, delivery_time_limit=0.75, max_batching_limit=mbl)
        orderDelivery_Vehicle.append(a.orderDelivery_vehicle)

        if p == 6 or p == 13 or p == 20 or p == 27:
            print("Calculating weekly incentives at the end of each week")
            for m, n in a.agent_dict.items():
                n.weekly_incentive(p)

        if p == 29:
            print("Adding the weekly incentives at the end")
            for m, n in a.agent_dict.items():
                print("Total earning without weekly incentives of agent", n.id, "is", n.total_earning)
                wi = sum(n.weeklyIncentives)
                n.total_earning += wi
                print("Total earning with weekly incentives is", n.total_earning)
        order_delay = order_delay + a.order_delayed_by
        #avg_delivery_tym = statistics.mean(a.delivery_time)
    chosenBicycleAgent = None
    chosenBikeAgent = None
    for m, n in a.agent_dict.items():
        if n.vehicle == 0:
            ovhng = n.work_hours + n.spawn_time - 24
            if ovhng > 0:
                actualworkhours = n.work_hours - ovhng
            else:
                actualworkhours = n.work_hours
            bikes += 1
            first_mile_bike += n.first_mile
            last_mile_bike += n.last_mile
            dead_mile_bike += n.dead_mile
            totalMiles = sum(n.first_mile) + sum(n.last_mile) + sum(n.dead_mile)
            parkingLoad_b = ((actualworkhours * iterations) - n.total_riding_time) / iterations
            parkingLoad_bike.append(parkingLoad_b)
            parked_tym_bike = parkingLoad_b / actualworkhours
            parked_time_ratio_bike.append(parked_tym_bike)
            del_tym_bike += n.delivery_time
            if mbl > 1:
                itrB = ((actualworkhours * iterations) - n.total_waiting_time - (sum(n.first_mile)/MOTORBIKE_KMH) - (sum(n.last_mile)/MOTORBIKE_KMH)) / (actualworkhours * iterations)
            else:
                itrB = ((actualworkhours * iterations) - sum(n.delivery_time)) / (actualworkhours * iterations)
            idleTymratioBike.append(itrB)
            agentearningperhourBike.append(n.total_earning / (actualworkhours * iterations))
            earningtablebike.append((actualworkhours, iterations, totalMiles, n.total_earning, n.total_earning / iterations,
                                 n.total_earning / (iterations * actualworkhours), sum(n.first_mile) , sum(n.last_mile), n.orders_delivered))
            if actualworkhours > 12:
                chosenBikeAgent = n

        elif n.vehicle == 1:
            ovhng = n.work_hours + n.spawn_time - 24
            if ovhng > 0:
                actualworkhours = n.work_hours - ovhng
            else:
                actualworkhours = n.work_hours
            cycles += 1
            first_mile_cycle += n.first_mile
            last_mile_cycle += n.last_mile
            dead_mile_cycle += n.dead_mile
            totalMiles = sum(n.first_mile) + sum(n.last_mile) + sum(n.dead_mile)
            parkingLoad_c = ((actualworkhours * iterations) - n.total_riding_time) / iterations
            parkingLoad_bicycle.append(parkingLoad_c)
            parked_tym_cycle = parkingLoad_c / actualworkhours
            parked_time_ratio_cycle.append(parked_tym_cycle)
            del_tym_cycle += n.delivery_time
            if mbl > 1:
                itrC = ((actualworkhours * iterations) - n.total_waiting_time - (sum(n.first_mile)/BICYCLE_KMH) - (sum(n.last_mile)/BICYCLE_KMH)) / (actualworkhours * iterations)
            else:
                itrC = ((actualworkhours * iterations) - sum(n.delivery_time)) / (actualworkhours * iterations)
            idleTymratioCycle.append(itrC)
            agentearningperhourBicycle.append(n.total_earning / (actualworkhours * iterations))
            earningtablebiycle.append((actualworkhours, iterations, totalMiles, n.total_earning, n.total_earning / iterations,
                                 n.total_earning / (iterations * actualworkhours), sum(n.first_mile) , sum(n.last_mile), n.orders_delivered))
            if actualworkhours > 8:
                chosenBicycleAgent = n

    #print("order  delivery vehicle", orderDelivery_Vehicle)
    print("Bicycle Orders", a.orders_fulfilled_bicycle)
    print("Bike Orders", a.orders_fulfilled_bike)
    print("Total batched orders & %", sum(a.orderBatches), sum(a.orderBatches)*100/(orderVol*iterations))
    orders_fulfilled = a.orders_fulfilled_bicycle + a.orders_fulfilled_bike
    print("Orders fulfilled %", (orders_fulfilled * 100) / (orderVol * iterations))
    print("first mile bike", sum(first_mile_bike)/ a.orders_fulfilled_bike, statistics.stdev(first_mile_bike))
    print("last mile bike", sum(last_mile_bike)/ a.orders_fulfilled_bike, statistics.stdev(last_mile_bike))
    print("dead mile bike", sum(dead_mile_bike)/ a.orders_fulfilled_bike, statistics.stdev(dead_mile_bike))
    print("Parked Time % bike", statistics.mean(parked_time_ratio_bike)*100, statistics.stdev(parked_time_ratio_bike)*100)
    print("Idle Time % bike", statistics.mean(idleTymratioBike)*100, statistics.stdev(idleTymratioBike)*100)
    print("Parking load, bike", sum(parkingLoad_bike), statistics.stdev(parkingLoad_bike))
    print("Avg. delivery time bike", statistics.mean(del_tym_bike)*60, statistics.stdev(del_tym_bike)*60)
    print("Special delivery time & count", statistics.mean(a.special_delivery_time)*60, len(a.special_delivery_time))
    #print(a.special_delivery_time)
    #print(del_tym_bike)
    print("Parking Load (vehicle hours) bikes", sum(parkingLoad_bike))
    agentearningperhourBike.sort()
    print("agentearningperhour Bike", agentearningperhourBike)
    print("Median, & Mean, & STDEV agentearningperhour", statistics.median(agentearningperhourBike), statistics.mean(agentearningperhourBike), statistics.stdev(agentearningperhourBike))
    earningDFbike = pd.DataFrame(earningtablebike, columns=['Actual Work hours', 'Days', 'Total Kms travelled', 'Total Earnings', 'Avg. Daily Earnings', 'Avg. Hourly Earnings', 'Total First Mile', 'Total Last Mile', 'Orders Delivered'])
    # earningDFbike.to_excel(str(orderVol) + "Ordr" + str(mbl) + "MBL" + str(wagerate) + "wgrt" + "500orderValidatn.xlsx")
    first_mile_bikeDF = pd.DataFrame(first_mile_bike, columns=['FirstMile'])
    last_mile_bikeDF = pd.DataFrame(last_mile_bike, columns=['LastMile'])
    # first_mile_bikeDF.to_excel("FM500orderValidatn.xlsx")
    # last_mile_bikeDF.to_excel("LM500orderValidatn.xlsx")
    #earningDFbike.to_excel(str(orderVol) + "Ordr" + str(wagerate) + "wgrt" + "VlidtnWdoutWeeklyIncentMetaC.xlsx")
    distVStimeDF = pd.DataFrame(chosenBikeAgent.distTimeGraph, columns=['x', 'y'])
    #distVStimeDF.to_excel(str(orderVol) + "Ordr" + str(iterations) + "Itr" + "2.5distVStimeGraphBikeMetaC.xlsx")
    print("################")
    if a.orders_fulfilled_bicycle > 0:
        print("first mile cycle", sum(first_mile_cycle)/ a.orders_fulfilled_bicycle, statistics.stdev(first_mile_cycle))
        print("last mile cycle", sum(last_mile_cycle)/ a.orders_fulfilled_bicycle, statistics.stdev(last_mile_cycle))
        print("dead mile cycle", sum(dead_mile_cycle)/ a.orders_fulfilled_bicycle, statistics.stdev(dead_mile_cycle))
        print("Parked Time % cycle", statistics.mean(parked_time_ratio_cycle), statistics.stdev(parked_time_ratio_cycle))
        print("Idle Time % cycle", statistics.mean(idleTymratioCycle), statistics.stdev(idleTymratioCycle))
        print("Parking load, cycle", sum(parkingLoad_bicycle), statistics.stdev(parkingLoad_bicycle))
        print("Avg. delivery time cycle", statistics.mean(del_tym_cycle)*60, statistics.stdev(del_tym_cycle)*60)
        print("Parking Load (vehicle hours) bikes", sum(parkingLoad_bicycle))
        agentearningperhourBicycle.sort()
        print("agentearningperhour Bicycles", agentearningperhourBicycle)
        print("Median, & Mean, & STDEV agentearningperhour", statistics.median(agentearningperhourBicycle), statistics.mean(agentearningperhourBicycle), statistics.stdev(agentearningperhourBicycle))
        distVStimeDF = pd.DataFrame(chosenBicycleAgent.distTimeGraph, columns=['x', 'y'])
        #distVStimeDF.to_excel(str(orderVol) + "Ordr" + str(iterations) + "Itr" + "2.5distVStimeGraphBicycleMetaC.xlsx")
        earningDFbicycle = pd.DataFrame(earningtablebiycle, columns=['Actual Work hours', 'Days', 'Total Kms travelled', 'Total Earnings', 'Avg. Daily Earnings', 'Avg. Hourly Earnings', 'Total First Mile', 'Total Last Mile', 'Orders Delivered'])
        #earningDFbicycle.to_excel(str(orderVol) + "Ordr" + str(iterations) + "Itr" + str(wagerate) + "wgrt" + "2.5ETBicylMetaC.xlsx")
    print("Bikes, Bicycles", bikes, cycles)
    #######
    # print(chosenBicycleAgent.distTimeGraph)
    parkingLoad_FBOwise = {x:0 for x in range(N_FBOS) if x==x}
    for m,n in a.agent_dict.items():
        print(n.parkingLoad_agentwise)
        for f in range(N_FBOS):
            parkingLoad_FBOwise[f] += n.parkingLoad_agentwise[f]
    print(parkingLoad_FBOwise)
    pl = 0
    for m,n in parkingLoad_FBOwise.items():
        pl += n
    print(pl/iterations)