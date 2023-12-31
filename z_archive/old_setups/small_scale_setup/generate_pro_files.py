import random
import json
import copy
import os





experiment = "proof_of_concept_experiment"

dry_run = False









# Cleanup previous files in directory as the number of objects may be less than before, 
# causing dead files from previous runs to still exist

if not dry_run:
    output_path = "small_scale_setup/nio_files"

    files = os.listdir(output_path)
    for file in files:
        file_path = os.path.join(output_path, file)
        if os.path.isfile(file_path):
            os.remove(file_path)

########################

# Lists of possible values

countries = [
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AW", "AX", "AZ", "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS", "BT", "BV", "BW", "BY", "BZ", "CA", "CC", "CD", "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN", "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM", "DO", "DZ", "EC", "EE", "EG", "EH", "ER", "ES", "ET", "FI", "FJ", "FK", "FM", "FO", "FR", "GA", "GB", "GD", "GE", "GF", "GG", "GH", "GI", "GL", "GM", "GN", "GP", "GQ", "GR", "GS", "GT", "GU", "GW", "GY", "HK", "HM", "HN", "HR", "HT", "HU", "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR", "IS", "IT", "JE", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN", "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME", "MF", "MG", "MH", "MK", "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA", "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG", "PH", "PK", "PL", "PM", "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW", "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI", "SJ", "SK", "SL", "SM", "SN", "SO", "SR", "SS", "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TF", "TG", "TH", "TJ", "TK", "TL", "TM", "TN", "TO", "TR", "TT", "TV", "TW", "TZ", "UA", "UG", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG", "VI", "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW" ]

# Generate random JSON objects
num_objects = 25
output_objects = []

features = [
        "filtering",
        "anti_spoofing",
        "coordination",
        "routing_information"
    ] 

ases = []
with open("small_scale_setup/data/as_numbers.txt", "r") as file:
    for line in file:
        ases.append(line[:-1])

for _ in range(num_objects):
    endpoints = random.sample(ases, 2)

    as_source = endpoints[0]
    as_destination = endpoints[1]

    # Requirements for privacy
    strict_requirements_amount = random.randint(0, len(features))
    strict_requirements = random.sample(features, strict_requirements_amount)

    other_requirements = [i for i in features if i not in strict_requirements]
    best_effort_requirements_amount = random.randint(min(len(other_requirements), 1), len(other_requirements))
    best_effort_requirements = random.sample(other_requirements, best_effort_requirements_amount)

    best_effort_mode = random.choice(["biggest_subset", "ordered_list"])
    
    geolocation_copy = copy.deepcopy(countries)

    geolocation_amount = random.randint(0, min(10, len(geolocation_copy)))
    geolocation_exclude = random.sample(geolocation_copy, geolocation_amount)
    geolocation_exclude.sort()
    
    path_optimization = random.choice(["minimize_total_latency", "minimize_number_of_hops", "none"])
    
    target_amount_of_paths = random.choice([1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 4, 5, 6])
    minimum_number_of_paths = 1

    fallback_to_ebgp = random.choice(["true", "false"])
    
    data = {
        "as_source": as_source,
        "as_destination": as_destination,
        "requirements": {
            "strict": strict_requirements,
            "best_effort": best_effort_requirements,
            "best_effort_mode": best_effort_mode
        },
        "geolocation": {
            "exclude": geolocation_exclude
        },
        "path_optimization": path_optimization,
        "multipath": {
            "target_amount_of_paths": target_amount_of_paths,
            "minimum_number_of_paths": minimum_number_of_paths
        },
        "fallback_to_ebgp_if_no_path_found": fallback_to_ebgp
    }
    
    output_objects.append(data)


# Print the generated JSON objects
if not dry_run:
    for i, obj in enumerate(output_objects):
        with open(f"small_scale_setup/{experiment}/pro_files/pro_{i:02}.json", "w") as file:
            file.write(f"{json.dumps(obj, indent=2)}")

