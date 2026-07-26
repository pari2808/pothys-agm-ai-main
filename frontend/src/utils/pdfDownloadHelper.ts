import { Platform, Alert } from 'react-native';
import apiClient from '../services/api';
import { useAuthStore } from '../store/authStore';

export async function downloadAndShareReport(reportId: string, branchName: string, reportDate: string) {
  const filename = `${branchName.replace(/\s+/g, '_')}_Report_${reportDate}.pdf`;

  if (Platform.OS === 'web') {
    try {
      const response = await apiClient.get(`/reports/${reportId}/download`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      Alert.alert("Success", "Report downloaded successfully.");
      return true;
    } catch (error) {
      console.error('Web PDF download failed:', error);
      throw error;
    }
  } else {
    try {
      const FileSystem = require('expo-file-system');
      const Sharing = require('expo-sharing');

      const token = useAuthStore.getState().token;
      const apiBaseUrl = apiClient.defaults.baseURL;
      
      const fileUri = `${FileSystem.documentDirectory}${filename}`;
      
      const downloadResult = await FileSystem.downloadAsync(
        `${apiBaseUrl}/reports/${reportId}/download`,
        fileUri,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (downloadResult.status === 200) {
        Alert.alert("Success", "Report downloaded successfully.");
        if (await Sharing.isAvailableAsync()) {
          await Sharing.shareAsync(downloadResult.uri, {
            mimeType: 'application/pdf',
            dialogTitle: `Share ${filename}`,
          });
        }
        return true;
      } else {
        throw new Error(`Download failed with status ${downloadResult.status}`);
      }
    } catch (error) {
      console.error('Mobile PDF download failed:', error);
      throw error;
    }
  }
}
