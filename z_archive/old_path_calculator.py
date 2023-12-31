import json
from types import SimpleNamespace
import networkx as nx
import copy
import matplotlib.pyplot as plt
from filterset import Filterset
from geopy import distance
import os
import random
import time
import math

# def calculate_total_latency(nio_objects, path):
#     if len(path) == 0:
#         return 0

#     total = 0
#     for i in range(len(path) - 1):
#         node0 = path[i]
#         node1 = path[i + 1] 

#         lat0 = nio_objects[node0].lat
#         lon0 = nio_objects[node0].lon
#         lat1 = nio_objects[node1].lat
#         lon1 = nio_objects[node1].lon

#         latency = spit_latency(lat0, lon0, lat1, lon1)
#         total += latency

#     return round(total)

# Utility method for checking path existence that does not explode if source or dest are removed due to 
# insufficiently supported features
# def safe_has_path(graph, source, dest) -> bool:
#     if source not in graph.nodes or dest not in graph.nodes:
#         return False
#     else:
#         return nx.has_path(graph, source, dest)

# def spit_latency(lat0, lon0, lat1, lon1):
#     result = distance.distance((lat0, lon0), (lat1, lon1))
#     miles = result.miles

#     # Method used: https://www.oneneck.com/blog/estimating-wan-latency-requirements/
#     # Added 0.5 instead of 2 as this resulted in results closer to this calculator:
#     # https://wintelguy.com/wanlat.html 
#     latency = round((miles * 1.1 + 200) * 2 / 124 + 0.5, 2)
    
#     return latency

# def fallback_to_ebgp(we_fallback_to_ebgp, verbose, reason_for_failure):
#     if verbose:
#         if we_fallback_to_ebgp:
#             print("No path is found, but the PRO does specify to fallback to EBGP, so the request will now be fulfilled by EBGP!")
#         else:
#             print("No path is found, and the PRO specifies that the request should NOT be forwarded to EBGP. Thus, it ends here. Bye!")
#     return (0, 0, reason_for_failure, 0, 0, 0, 0, 0, 0)





def calculate_paths(path_to_nio_files: str, pro, pro_index, print_all = "no_pls"):

    time_start = time.time()

    verbose = print_all == "verbose"
    if verbose:
        print("checking pro from", pro.as_source, "to", pro.as_destination)
    
    we_fallback_to_ebgp = pro.fallback_to_ebgp_if_no_path_found == "true"

    # Generate NIO objects
    nio_objects = {}
    as_numbers = []
    edges = []

    for _,_,files in os.walk(path_to_nio_files):
        for file in files:
            with open(path_to_nio_files + file, "r") as nio_file:
                nio_content = nio_file.read()
                nio_object = json.loads(nio_content, object_hook=lambda nio_content: SimpleNamespace(**nio_content))

                as_numbers.append(nio_object.as_number)

                if "scalability_experiment" in path_to_nio_files:
                    nio_object.features = []


                nio_objects[nio_object.as_number] = nio_object
                    

                for index, outgoing_edge in enumerate(nio_object.connections):

                    # This can be updated later when edge data _is_ needed. For now its empty.
                    edge_data = {
                        # Add stuff when needed
                    }

                    edge_entry = [nio_object.as_number, outgoing_edge, edge_data]
                    edges.append(edge_entry)

    # Build graph
    G = nx.Graph()
    G.add_nodes_from(as_numbers)
    G.add_edges_from(edges)

    time_after_building_graph = time.time()

    #############################################################################################################
    ######## STRICT PHASE #######################################################################################
    #############################################################################################################

    
    if verbose:
        print("\n### STRICT PHASE ###\n")

    filterset = Filterset(pro)
    subset_generation_runtime = filterset.best_effort_subset_generation_time

    # Drop nodes that do not comply with strict requirements
    G_strict_phase = filterset.apply_strict_filters(G, pro, nio_objects)

    if G_strict_phase is None:
        if verbose:
            print("No path that adheres to the strict requirements can be found!")

        return fallback_to_ebgp(we_fallback_to_ebgp, verbose, "strict was too strict")
        exit(0)
    else:
        if verbose:
            print("At least one path that adheres to strict requirements", filterset.strict_requirements, "exists! Continuing with the best-effort phase!")

    time_after_strict_phase = time.time()

    #############################################################################################################
    ######## BEST EFFORT PHASE ##################################################################################
    #############################################################################################################

    if verbose:
        print("\n### BEST EFFORT PHASE ###\n")

    result = filterset.calculate_biggest_satisfiable_subset(G_strict_phase, pro, nio_objects)

    G_best_effort_phase = result[0]
    satisfied_requirements = result[1]
    number_of_subsets = result[2]

    if verbose:
        if len(satisfied_requirements) > 0:
            print(f"We could satisfy the best-effort requirements {satisfied_requirements}!")
        else:
            print("No extra best-effort requirements could be satisfied.")

        print("Now, on to the optimization phase!")


    time_after_best_effort_phase = time.time()

    #######################################################################
    ######## Scoring phase ###########################################
    #######################################################################

    if verbose:
        print("\n### SCORING PHASE ###\n")

    G_after_filter = copy.deepcopy(G_best_effort_phase)

    # Find all available link-disjoint paths
    all_disjoint_paths = []
    if pro.path_optimization == "none":
        all_disjoint_paths = list(nx.edge_disjoint_paths(G_after_filter, pro.as_source, pro.as_destination, cutoff=pro.multipath.target_amount_of_paths))
    else:
        all_disjoint_paths = list(nx.edge_disjoint_paths(G_after_filter, pro.as_source, pro.as_destination))


    default_path = all_disjoint_paths[0]

    # SKIP IF STRATEGY IS NONE
    if pro.path_optimization != "none":

        # Score paths based on the chosen metric & pass on to the multipath pruning phase
        scored_paths = []


        if pro.path_optimization == "minimize_total_latency":
            for path in all_disjoint_paths:
                scored_paths.append([path, calculate_total_latency(nio_objects, path)])
        else: # scoring strategy is minimize nr of hops or none, in which case we also minimize hops
            for path in all_disjoint_paths:
                scored_paths.append([path, len(path) - 1])

        # sort scored_paths list by score
        scored_paths.sort(key = lambda x: x[1])

        if verbose:
            if pro.path_optimization == "none":
                print("Here are all possible link-disjoint paths, scored based on the selected optimization strategy (which was none, so defaulting to minimize_number_of_hops):")

            else:
                print("Here are all possible link-disjoint paths, scored based on the selected scoring strategy (which was", pro.path_optimization + "):")

        for path in scored_paths:
            if verbose:
                print(path)

    else:
        if verbose:
            print("We skipped scoring phase since the scoring strategy was: none")
        scored_paths = list(all_disjoint_paths)

    
    time_after_scoring_phase = time.time()

    #######################################################################
    ######## Multipath stage ##############################################
    #######################################################################

    if verbose:
        print("\n### MULTIPATH PHASE ###\n")

    target_nr_of_paths = pro.multipath.target_amount_of_paths

    multipath_selection = []
    until = 1 # Take one path if not adjusted

    if target_nr_of_paths == 0:
        until = len(scored_paths)
    elif len(scored_paths) <= target_nr_of_paths:
        until = len(scored_paths)
    else:
        until = target_nr_of_paths

    multipath_selection.extend(scored_paths[:until])

    if verbose:
        print("Here are the", len(multipath_selection), "best paths:")
        for path in multipath_selection:
            print(path)

    ###################################################################################################################
    # Generate pathstring formatted as: 
    #    as1;as2;...;asn-latency|as1;as2;...;asn-latency|...|as1;as2;...;asn-latency#shortest;path;no;constraints-latency#fastest;path;no;constraints-latency,NumberOfBestEffortRequirements,BestEffortSubsetGenerationTimeInSeconds,runtime_of_filter,chosen_as_path_latency,chosen_as_path_nr_hops,default_path_nr_hops,default_path_latency

    paths_as_string = ""
    path_list = scored_paths
    
    for index, path in enumerate(path_list):

        while isinstance(path[0], list):
            path = path[0]
        path_string = ""
        for i in range(len(path) - 1):
            path_string += str(path[i]) + ";"
        path_string += str(path[len(path) - 1]) + "-"
        
        # calculate latency
        latency = calculate_total_latency(nio_objects, path)
        path_string += str(round(latency))

        paths_as_string += path_string
        if index < len(path_list) - 1:
            paths_as_string += "|"

    # Add shortest path without any constraints for 'Cost of control' experiment
    shortest_path_no_constraints = nx.shortest_path(G, pro.as_source, pro.as_destination)
    paths_as_string += "#"
    for index, asn in enumerate(shortest_path_no_constraints):
        paths_as_string += asn
        if index < len(shortest_path_no_constraints) - 1:
            paths_as_string += ";"
    
    paths_as_string += "-"
    shortest_path_no_constraints_latency = calculate_total_latency(nio_objects, shortest_path_no_constraints)
    paths_as_string += str(round(shortest_path_no_constraints_latency))
    paths_as_string += "#"

    # Add fastest path without any constraints for 'Cost of control' experiment
    all_disjoint_paths_no_constraints = nx.edge_disjoint_paths(G, pro.as_source, pro.as_destination)

    scored_paths = []
    for path in all_disjoint_paths_no_constraints:
        scored_paths.append([path, calculate_total_latency(nio_objects, path)])
    
    scored_paths.sort(key = lambda x: x[1])
    fastest_path_no_constraints = scored_paths[0][0]
    fastest_path_no_constraints_latency = scored_paths[0][1]

    for index, asn in enumerate(fastest_path_no_constraints):
        paths_as_string += asn
        if index < len(fastest_path_no_constraints) - 1:
            paths_as_string += ";"

    paths_as_string += "-"
    paths_as_string += str(round(fastest_path_no_constraints_latency))

    # Scalability experiment data
    paths_as_string += "," + str(len(pro.requirements.best_effort)) + "," + str(round(subset_generation_runtime, 3)) + "," + str(round(number_of_subsets, 3))

    if pro_index < 50:
        # As path experiment:
        with open("full_scale_setup/data/chosen_as_paths.csv", "r") as file:
            chosen_paths = file.readlines()
            c_path = chosen_paths[pro_index][:-1]
            chosen_path = c_path.split(",")
            chosen_path_latency = round(calculate_total_latency(nio_objects, chosen_path))
            chosen_path_nr_hops = len(chosen_path)

            paths_as_string += "," + str(chosen_path_latency) + "," + str(chosen_path_nr_hops)
    else:
        path_as_string += ",0,0"

    # Cost of optimization experiment
    nr_hops_default_path = len(default_path)
    latency_of_default_path = round(calculate_total_latency(nio_objects, default_path))

    paths_as_string += "," + str(nr_hops_default_path) + "," + str(latency_of_default_path)

    round_decimals = 2
    return (
        len(scored_paths), 
        len(multipath_selection), 
        "success", 
        round(time_after_building_graph - time_start, round_decimals),
        round(time_after_strict_phase - time_after_building_graph, round_decimals),
        round(time_after_best_effort_phase - time_after_strict_phase, round_decimals),
        round(time_after_scoring_phase - time_after_best_effort_phase, round_decimals),
        round(time_after_scoring_phase - time_start, round_decimals),
        paths_as_string)



