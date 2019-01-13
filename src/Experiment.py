import os
import sys
import time
import tempfile
from src.Island import Island
from src.utilities import decode_stdout, get_date_in_string, clean_dir, kill_all_processes, open_processes


class Experiment():
	def __init__(self, experiment_xml_config, evaluators_xml_config, name):
		self.start_t = time.time()
		self.tmp_dir = tempfile.mkdtemp(dir='/tmp')

		# Experiment settings
		self.max_fitness        = int(experiment_xml_config.attrib['max_fitness'])
		self.max_time           = int(experiment_xml_config.attrib['max_time'])
		self.chromosome_length  = int(experiment_xml_config.attrib['chromosome_length'])
		self.experiment_name    = name

		# Islands settings
		self.island_configs = []
		self.islands        = self.initialize_islands(experiment_xml_config, evaluators_xml_config)
		for island in self.islands:
			open_processes(island)

		# Logs
		self.log = self.initialize_log()

	def initialize_islands(self, experiment, evaluators):
		return [Island(name, island, self.chromosome_length, evaluators, self.tmp_dir) for name, island in enumerate(experiment)]

	def termination_check(self, island):
			if island.individuals[0][0] >= self.max_fitness != 0:
				self.termination_printout(island, 'fitness')
				return True
			elif self.max_time < time.time() - self.start_t and self.max_time != 0:
				self.termination_printout(island, 'timeout')
				return True
			else:
				return False

	def termination_printout(self, island, reason):
		if reason == 'timeout':
			print('Evolution terminated: timeout.')
		else:
			print('Evolution terminated: maximum fitness has been achieved.')
		print('Generated', island.generation, 'generations in', "{:.2f}".format(time.time() - self.start_t), 'seconds.')
		self.print_migration_success_rates()
		print('Individuals of the last generation:\n')
		self.print_all_individuals()

	def print_migration_success_rates(self):
		rates = [i.replacement_policy.migration_policy.get_success_rate() for i in self.islands]
		print('Migration success rates', ["{:.2f} %".format(rate) for rate in rates])

	def initialize_log(self):
		path = 'exp/logs/' + self.experiment_name
		logfile = open(path + '_' + get_date_in_string() + '.log', 'w')
		logfile.write("configs\n")

		return logfile

	def update_log(self, island):
		self.log.write(str(island.generation) + ',' + str(island.island_name) + ',' +
					   str(island.individuals[0]) + ',' + str(island.individuals[1]) + '\n')

	def print_all_individuals(self):
		for island in self.islands:
			print('island [ ' + str(island.island_name) + ' ]')
			for individual in island.individuals:
				print(individual)

	def run(self):
			for island in self.islands:
				if len(island.processes) > 0:
					self.collect_fitness(island)
				else:
					self.organize_island(island)
					if self.termination_check(island):
						self.quit_experiment()
					else:
						self.next_generation(island)

	def organize_island(self, island):
		island.sort_individuals()
		self.update_log(island)

	def next_generation(self, island):
		island.replacement_policy.migration_policy.migrate_out(island.individuals)
		island.evolve()
		open_processes(island)

	def collect_fitness(self, island):
		for process in island.processes:
			if process.poll():
				index, fitness = decode_stdout(process.communicate()[0])
				island.individuals[int(index)][0] = int(fitness)
				island.individuals[int(index)][2] = True
				island.processes.remove(process)

	def quit_experiment(self):
		for island in self.islands:
			kill_all_processes(island.processes)
			clean_dir(self.tmp_dir)
		os.removedirs(self.tmp_dir)
		sys.exit()