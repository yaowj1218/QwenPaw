import { useState, useEffect } from "react";
import { useAppMessage } from "../../../../hooks/useAppMessage";
import { useTranslation } from "react-i18next";
import api from "../../../../api";
import type {
  MarkdownFile,
  DailyMemoryFile,
  CommonInfoFile,
} from "../../../../api/types";
import { workspaceApi } from "../../../../api/modules/workspace";
import { useAgentStore } from "../../../../stores/agentStore";

// Returns the parent directory of a file path, supporting both '/' and '\' separators.
const getParentDir = (filePath: string): string => {
  const match = filePath.match(/^(.*)[/\\]/);
  return match ? match[1] : filePath;
};

const isCommonInfoPath = (filePath: string): boolean =>
  /(^|[/\\])common_info[/\\]/i.test(filePath);

const isCommonInfoIndexFile = (filename: string): boolean =>
  filename.toLowerCase() === "common_info.md";

const isMemoryIndexFile = (filename: string): boolean =>
  filename.toLowerCase() === "memory.md";

const getWorkspaceDirFromCommonInfoPath = (filePath: string): string => {
  const commonInfoDir = getParentDir(filePath);
  return getParentDir(commonInfoDir);
};

export const useAgentsData = () => {
  const { t } = useTranslation();
  const { selectedAgent } = useAgentStore();
  const [files, setFiles] = useState<MarkdownFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<MarkdownFile | null>(null);
  const [dailyMemories, setDailyMemories] = useState<DailyMemoryFile[]>([]);
  const [expandedMemory, setExpandedMemory] = useState(false);
  const [commonInfoFiles, setCommonInfoFiles] = useState<CommonInfoFile[]>([]);
  const [expandedCommonInfo, setExpandedCommonInfo] = useState(false);
  const [fileContent, setFileContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [workspacePath, setWorkspacePath] = useState<string | null>(null);
  const [enabledFiles, setEnabledFiles] = useState<string[]>([]);
  const { message } = useAppMessage();

  useEffect(() => {
    const initializeData = async () => {
      // Remember currently selected file name
      const previouslySelectedFilename = selectedFile?.filename;

      // Clear content first
      setFileContent("");
      setOriginalContent("");
      setExpandedMemory(false);
      setExpandedCommonInfo(false);
      setCommonInfoFiles([]);

      const enabled = await fetchEnabledFiles();
      const [fileList, commonInfoList] = await Promise.all([
        workspaceApi.listFiles(),
        api.listCommonInfo(),
      ]);
      setCommonInfoFiles(commonInfoList);
      const displayFiles = withCommonInfoRoot(
        fileList as unknown as MarkdownFile[],
        commonInfoList,
      );
      const sortedFiles = sortFilesByEnabled(displayFiles, enabled);
      setFiles(sortedFiles);

      // Set workspace path (handle both Unix '/' and Windows '\' separators)
      if (displayFiles.length > 0) {
        setWorkspacePath(getParentDir(displayFiles[0].path));
      } else {
        setWorkspacePath("");
      }

      // Try to re-select the same file in new workspace
      if (previouslySelectedFilename) {
        const sameFile = sortedFiles.find(
          (f) => f.filename === previouslySelectedFilename,
        );
        if (sameFile) {
          // Auto-load the same file from new workspace
          await handleFileClick(sameFile);
        } else {
          // File doesn't exist in new workspace, clear selection
          setSelectedFile(null);
        }
      } else {
        setSelectedFile(null);
      }
    };
    initializeData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAgent]);

  // Re-sort when enabledFiles changes (for toggle/reorder operations)
  useEffect(() => {
    if (files.length > 0 && enabledFiles.length >= 0) {
      const sortedFiles = sortFilesByEnabled(files, enabledFiles);

      // Only update if order actually changed to avoid infinite loop
      const orderChanged = sortedFiles.some(
        (file, index) => file.filename !== files[index]?.filename,
      );
      if (orderChanged) {
        setFiles(sortedFiles);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabledFiles]);

  const fetchEnabledFiles = async () => {
    try {
      const result = await workspaceApi.getSystemPromptFiles();
      const enabled = Array.isArray(result) ? result : [];
      setEnabledFiles(enabled);
      return enabled;
    } catch (error) {
      console.error("Failed to fetch enabled files", error);
      return [];
    }
  };

  const sortFilesByEnabled = (
    fileList: MarkdownFile[],
    currentEnabledFiles: string[],
  ) => {
    const safeEnabled = Array.isArray(currentEnabledFiles)
      ? currentEnabledFiles
      : [];
    return [...fileList].sort((a, b) => {
      const aIndex = safeEnabled.indexOf(a.filename);
      const bIndex = safeEnabled.indexOf(b.filename);
      const aEnabled = aIndex !== -1;
      const bEnabled = bIndex !== -1;

      if (aEnabled && bEnabled) {
        return aIndex - bIndex;
      }
      if (aEnabled) return -1;
      if (bEnabled) return 1;
      return a.filename.localeCompare(b.filename);
    });
  };

  const withCommonInfoRoot = (
    fileList: MarkdownFile[],
    commonInfoList: CommonInfoFile[],
  ) => {
    if (
      fileList.some((file) => isCommonInfoIndexFile(file.filename)) ||
      commonInfoList.length === 0
    ) {
      return fileList;
    }

    const latestCommonInfo = [...commonInfoList].sort(
      (a, b) => b.updated_at - a.updated_at,
    )[0];
    const workspaceDir = getWorkspaceDirFromCommonInfoPath(
      latestCommonInfo.path,
    );

    return [
      ...fileList,
      {
        filename: "COMMON_INFO.md",
        path: `${workspaceDir}/COMMON_INFO.md`,
        size: 0,
        created_time: latestCommonInfo.created_time,
        modified_time: latestCommonInfo.modified_time,
        updated_at: latestCommonInfo.updated_at,
        virtual: true,
      },
    ];
  };

  const fetchFiles = async (latestEnabledFiles?: string[]) => {
    try {
      // Validate with Array.isArray: onClick handlers may pass a MouseEvent as the first argument
      const enabled = Array.isArray(latestEnabledFiles)
        ? latestEnabledFiles
        : await fetchEnabledFiles();
      const [fileList, commonInfoList] = await Promise.all([
        workspaceApi.listFiles(),
        api.listCommonInfo(),
      ]);
      setCommonInfoFiles(commonInfoList);
      const displayFiles = withCommonInfoRoot(
        fileList as unknown as MarkdownFile[],
        commonInfoList,
      );
      const sortedFiles = sortFilesByEnabled(displayFiles, enabled);
      setFiles(sortedFiles);
      // Set workspace path (handle both Unix '/' and Windows '\' separators)
      if (displayFiles.length > 0) {
        setWorkspacePath(getParentDir(displayFiles[0].path));
      } else {
        setWorkspacePath("");
      }
    } catch (error) {
      console.error("Failed to fetch files", error);
      message.error("Failed to load file list");
    }
  };

  const fetchDailyMemories = async () => {
    try {
      const memoryList = await api.listDailyMemory();
      setDailyMemories(memoryList);
    } catch (error) {
      console.error("Failed to fetch daily memories", error);
      message.error("Failed to load memory list");
    }
  };

  const fetchCommonInfoFiles = async () => {
    try {
      const commonInfoList = await api.listCommonInfo();
      setCommonInfoFiles(commonInfoList);
    } catch (error) {
      console.error("Failed to fetch common info files", error);
      message.error("Failed to load common info list");
    }
  };

  const handleFileClick = async (file: MarkdownFile) => {
    if (isMemoryIndexFile(file.filename)) {
      if (expandedMemory && isMemoryIndexFile(selectedFile?.filename ?? "")) {
        setExpandedMemory(false);
        return;
      } else {
        setExpandedMemory(true);
        fetchDailyMemories();
      }
    }

    if (isCommonInfoIndexFile(file.filename)) {
      if (
        expandedCommonInfo &&
        isCommonInfoIndexFile(selectedFile?.filename ?? "")
      ) {
        setExpandedCommonInfo(false);
        return;
      } else {
        setExpandedCommonInfo(true);
        fetchCommonInfoFiles();
      }
      if (file.virtual) {
        setSelectedFile(file);
        setFileContent("");
        setOriginalContent("");
        return;
      }
    }

    setSelectedFile(file);
    setLoading(true);
    try {
      const data = await workspaceApi.loadFile(file.filename);
      setFileContent(data.content);
      setOriginalContent(data.content);
    } catch (error) {
      console.error("Failed to load file", error);
      message.error("Failed to load file");
    } finally {
      setLoading(false);
    }
  };

  const handleDailyMemoryClick = async (daily: DailyMemoryFile) => {
    setSelectedFile({
      filename: `${daily.date}.md`,
      path: daily.path,
      size: daily.size,
      created_time: daily.created_time,
      modified_time: daily.modified_time,
      updated_at: daily.updated_at,
    });
    setLoading(true);
    try {
      const data = await api.loadDailyMemory(daily.date);
      setFileContent(data.content);
      setOriginalContent(data.content);
    } catch (error) {
      console.error("Failed to load daily memory", error);
      message.error("Failed to load daily memory");
    } finally {
      setLoading(false);
    }
  };

  const handleCommonInfoClick = async (commonInfo: CommonInfoFile) => {
    setSelectedFile({
      filename: commonInfo.filename,
      path: commonInfo.path,
      size: commonInfo.size,
      created_time: commonInfo.created_time,
      modified_time: commonInfo.modified_time,
      updated_at: commonInfo.updated_at,
    });
    setLoading(true);
    try {
      const data = await api.loadCommonInfo(commonInfo.filename);
      setFileContent(data.content);
      setOriginalContent(data.content);
    } catch (error) {
      console.error("Failed to load common info", error);
      message.error("Failed to load common info");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!selectedFile) return;
    setLoading(true);
    try {
      if (isCommonInfoPath(selectedFile.path)) {
        await api.saveCommonInfo(selectedFile.filename, fileContent);
      } else if (selectedFile.filename.match(/^\d{4}-\d{2}-\d{2}\.md$/)) {
        const date = selectedFile.filename.replace(".md", "");
        await api.saveDailyMemory(date, fileContent);
      } else {
        await api.saveFile(selectedFile.filename, fileContent);
      }
      setOriginalContent(fileContent);
      message.success("Saved successfully");
      if (isCommonInfoPath(selectedFile.path)) {
        fetchCommonInfoFiles();
      } else if (selectedFile.filename.match(/^\d{4}-\d{2}-\d{2}\.md$/)) {
        fetchDailyMemories();
      } else {
        fetchFiles();
      }
    } catch (error) {
      console.error("Failed to save file", error);
      message.error("Failed to save");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFileContent(originalContent);
  };

  const handleToggleFileEnabled = async (filename: string) => {
    const isEnabling = !enabledFiles.includes(filename);

    // Show warning for MEMORY.md
    if (isEnabling && isMemoryIndexFile(filename)) {
      message.warning({
        content: t("workspace.memoryFileWarning"),
        duration: 5,
      });
    }

    const newEnabledFiles = enabledFiles.includes(filename)
      ? enabledFiles.filter((f) => f !== filename)
      : [...enabledFiles, filename];

    try {
      await workspaceApi.setSystemPromptFiles(newEnabledFiles);
      setEnabledFiles(newEnabledFiles);
      message.success(
        t("workspace.configUpdated") || "System prompt configuration updated",
      );
    } catch (error) {
      console.error("Failed to update system prompt files", error);
      message.error(
        t("workspace.configUpdateFailed") ||
          "Failed to update system prompt configuration",
      );
    }
  };

  const handleReorderFiles = async (newOrder: string[]) => {
    try {
      await workspaceApi.setSystemPromptFiles(newOrder);
      setEnabledFiles(newOrder);
    } catch (error) {
      console.error("Failed to reorder files", error);
      message.error("Failed to update file order");
    }
  };

  const hasChanges = fileContent !== originalContent;

  return {
    files,
    selectedFile,
    dailyMemories,
    expandedMemory,
    commonInfoFiles,
    expandedCommonInfo,
    fileContent,
    loading,
    workspacePath,
    hasChanges,
    enabledFiles,
    setFileContent,
    fetchFiles,
    fetchDailyMemories,
    fetchCommonInfoFiles,
    handleFileClick,
    handleDailyMemoryClick,
    handleCommonInfoClick,
    handleSave,
    handleReset,
    handleToggleFileEnabled,
    handleReorderFiles,
  };
};
