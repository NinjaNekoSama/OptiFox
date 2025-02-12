import React, { useState } from "react";

// Props for the SearchBar component
type SearchBarProps = {
  onSearch: (query: string) => void; // Function to handle search submissions
};

// Style types for the SearchBar component
export type SearchStyle = {
  form: string;
  container: string;
  iconContainer: string;
  icon: string;
  inputContainer: string;
  input: string;
  button: string;
};

// Functional SearchBar component
const SearchBar: React.FC<SearchBarProps> = ({ onSearch }) => {
  const [query, setQuery] = useState(""); // State for the search query

  // Update query state on input change
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(event.target.value);
  };

  // Handle form submission to trigger search
  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSearch(query);
  };

  // Handle button click to trigger search
  const handleButtonClick = () => {
    onSearch(query);
  };

  // Define class names for styling elements
  const classNames: SearchStyle = {
    form: "relative rounded-sm bg-white px-[35px] py-[5px] shadow-md w-[30%]",
    container: "flex items-center",
    iconContainer:
      "pointer-events-none absolute inset-y-0 left-[16px] flex items-center pr-3",
    icon: "w-[12px] h-[12px]",
    inputContainer: "relative flex-1",
    input:
      "w-full text-[12px] font-[500] leading-[20px] text-[#374151] outline-none placeholder:text-[#94A3B8] py-[5px] px-[30px]",
    button:
      "bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline ml-2",
  };

  return (
    <div className="flex">
      <form
        onSubmit={handleSubmit}
        role="search"
        aria-label="Search clients"
        className={classNames.form}
      >
        <div className={classNames.container}>
          <div className={classNames.iconContainer}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 12 12"
              fill="none"
              className={classNames.icon}
            >
              <path
                d="M10.5 10.5L8.34998 8.34998M9.5 5.5C9.5 7.70914 7.70914 9.5 5.5 9.5C3.29086 9.5 1.5 7.70914 1.5 5.5C1.5 3.29086 3.29086 1.5 5.5 1.5C7.70914 1.5 9.5 3.29086 9.5 5.5Z"
                stroke="#64748B"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div className={classNames.inputContainer}>
            <label htmlFor="search" className="sr-only">
              Search Clients
            </label>
            <input
              type="text"
              id="search"
              value={query}
              onChange={handleChange}
              placeholder="Enter Stay ID..."
              className={classNames.input}
            />
          </div>
        </div>
      </form>

      <button
        type="button"
        className={classNames.button}
        onClick={handleButtonClick}
      >
        Search
      </button>
    </div>
  );
};

export default SearchBar;
