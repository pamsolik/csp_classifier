import mne
import numpy as np
import pandas as pd

from classifiers.flat import process
from config import configurations, experiment_frequency_range, subject_to_analyze
from data_classes.subject import Subject
from preprocessing.validate_available_electrodes import validate_available_electrodes
from visualization.accuracy_over_bands import visualize_accuracy_over_bands


def get_individual_accuracy(predicions, correct):
    all = [0, 0, 0]
    cor = [0, 0, 0]
    for i in range(len(predicions)):
        all[correct[i]] += 1
        if predicions[i] == correct[i]:
            cor[predicions[i]] += 1
    results = [2, 2, 2]
    if all[0] > 0: results[0] = cor[0] / all[0]
    if all[1] > 0: results[1] = cor[1] / all[1]
    if all[2] > 0: results[2] = cor[2] / all[2]
    return results


def create_confusion_matrix(n_classes, predictions_sets, corrects_sets):
    confusion_matrix = np.zeros((n_classes, n_classes))
    for fold_index in range(len(predictions_sets)):
        predictions = predictions_sets[fold_index]
        corrects = corrects_sets[fold_index]
        for index in range(len(predictions)):
            confusion_matrix[predictions[index]][corrects[index]] += 1
    return confusion_matrix


def calculate_recall(predictions, corrects, hand):
    numerator = 0
    denominator = 0
    for i in range(len(predictions)):
        if hand == corrects[i]:  # Actual condition: Positive
            if predictions[i] == corrects[i]:  # Predicted condition: Positive
                numerator += 1  # TP
            denominator += 1  # TP + FN
    if denominator == 0: return 0, 0
    return numerator, denominator


def calculate_precision(predictions, corrects, hand):
    numerator = 0
    denominator = 0
    for i in range(len(predictions)):
        if hand == predictions[i]:  # Predicted condition: Positive
            if predictions[i] == corrects[i]:  # Actual condition: Positive
                numerator += 1  # TP
            denominator += 1  # TP + FP
    if denominator == 0: return 0, 0
    return numerator, denominator


def calculate_combined_recall(predictions, corrects):
    recall_data = []
    for i in range(3):
        recall_data.append(calculate_recall(predictions, corrects, i))
    numerator = 0
    denominator = 0
    for i in recall_data:
        numerator += i[0]
        denominator += i[1]
    if denominator == 0: return 0
    return numerator / denominator


def calculate_combined_precision(predictions, corrects):
    recall_data = []
    for i in range(3):
        recall_data.append(calculate_precision(predictions, corrects, i))
    numerator = 0
    denominator = 0
    for i in recall_data:
        numerator += i[0]
        denominator += i[1]
    if denominator == 0: return 0
    return numerator / denominator


def analyze_data(bands, selected_electrodes):
    precision_numerator = [0, 0]
    precision_denominator = [0, 0]
    recall_numerator = [0, 0]
    recall_denominator = [0, 0]

    subject = Subject(subject_to_analyze)
    channels = validate_available_electrodes(subject, selected_electrodes)

    window_times, window_scores, csp_filters, epochs_info, predictions, corrects, _, _ = process(subject,
                                                                                                 bands, channels)

    for i in range(len(predictions)):
        for j in range(2):
            nprec, dprec = calculate_precision(predictions[i], corrects[i], j)
            nrec, drec = calculate_recall(predictions[i], corrects[i], j)
            precision_numerator[j] = precision_numerator[j] + nprec
            precision_denominator[j] = precision_denominator[j] + dprec
            recall_numerator[j] = recall_numerator[j] + nrec
            recall_denominator[j] = recall_denominator[j] + drec

    combined_accuracy_nominator = 0
    combined_accuracy_denumerator = 0
    accuracies = []
    for i in range(len(predictions)):
        accuracy_nominator = 0
        accuracy_denumerator = 0
        for j in range(len(predictions[i])):
            accuracy_denumerator += 1
            if predictions[i][j] == corrects[i][j]:
                accuracy_nominator += 1
        accuracies.append(accuracy_nominator/accuracy_denumerator)
        combined_accuracy_nominator += accuracy_nominator
        combined_accuracy_denumerator += accuracy_denumerator

    print('Accuracy: {}'.format(combined_accuracy_nominator / combined_accuracy_denumerator))

    final_precision = [0, 0]
    final_recall = [0, 0]
    for i in range(2):
        if precision_denominator[i] == 0:
            final_precision[i] = 0
        else:
            final_precision[i] = precision_numerator[i] / precision_denominator[i]

    for i in range(2):
        if recall_denominator[i] == 0:
            final_recall[i] = 0
        else:
            final_recall[i] = recall_numerator[i] / recall_denominator[i]

    print('Combined precision for movement class: {}'.format(final_precision[0]))
    print('Combined precision for rest class: {}'.format(final_precision[1]))

    print('Combined recall for movement class: {}'.format(final_recall[0]))
    print('Combined recall for rest class: {}'.format(final_recall[1]))

    return accuracies


def configuration_to_label(config):
    channels = config['channels']
    if len(channels) == 0:
        channels = 'all'
    else:
        channels = len(channels)
    return '{}Hz width {} channels'.format(
        config['band_width'],
        channels)


labels = list(map(configuration_to_label, configurations))

accuracy_data = {'accuracy': [], 'frequency': [], 'configuration': []}
for frequency in range(experiment_frequency_range[0], experiment_frequency_range[1]):
    for index, configuration in enumerate(configurations):
        accuracies = analyze_data(
            [(frequency, frequency + configuration['band_width'])],
            configuration['channels']
        )
        for accuracy in accuracies:
            accuracy_data['accuracy'].append(accuracy)
            accuracy_data['frequency'].append((frequency + frequency + configuration['band_width']) / 2)
            accuracy_data['configuration'].append(labels[index])

mne.set_log_level('warning')
accuracy_data = pd.DataFrame(data=accuracy_data)
visualize_accuracy_over_bands(accuracy_data)
