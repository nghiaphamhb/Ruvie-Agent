import { FileUp } from "lucide-react";
import { useState } from "react";
import { uploadDocument } from "../../api/ruvieApi";

export default function UploadPanel({ onUploaded }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  async function handleUpload() {
    if (!file) return;

    setUploading(true);

    try {
      await uploadDocument(file);
      onUploaded?.(`Uploaded ${file.name} successfully.`);
      setFile(null);
    } catch (error) {
      onUploaded?.(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="upload-panel">
      <label className="upload-label">
        <FileUp size={18} />
        <span>{file ? file.name : "Choose document"}</span>
        <input
          type="file"
          onChange={(event) => {
            const selectedFile = event.target.files[0];
            if (selectedFile) {
              setFile(selectedFile);
            }
          }}
        />
      </label>

      <button className="upload-button" onClick={handleUpload} disabled={!file || uploading}>
        {uploading ? "Uploading..." : "Upload"}
      </button>
    </div>
  );
}
